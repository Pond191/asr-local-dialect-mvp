# asr-local-dialect-mvp/backend/app.py
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, Dict
import tempfile
import os
import logging
import asyncio
from pathlib import Path

from asr_pipeline import transcribe
from postprocess import apply_mode

# ตั้งค่า logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="ASR Local Dialect — MVP")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# กำหนดขนาดไฟล์สูงสุด (500MB)
MAX_FILE_SIZE = 500 * 1024 * 1024

def _to_srt(segments: List[Dict]) -> str:
    """แปลง segments เป็นรูปแบบ SRT"""
    def ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    
    lines: List[str] = []
    for i, s in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{ts(s['start'])} --> {ts(s['end'])}")
        lines.append(s.get("text", ""))
        lines.append("")
    return "\n".join(lines)

def _to_vtt(segments: List[Dict]) -> str:
    """แปลง segments เป็นรูปแบบ VTT"""
    def ts(t: float) -> str:
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"
    
    lines: List[str] = ["WEBVTT", ""]
    for s in segments:
        lines.append(f"{ts(s['start'])} --> {ts(s['end'])}")
        lines.append(s.get("text", ""))
        lines.append("")
    return "\n".join(lines)

async def save_upload_file_chunked(upload_file: UploadFile, destination: Path) -> int:
    """บันทึกไฟล์แบบ chunked เพื่อประหยัดหน่วยความจำ"""
    total_size = 0
    chunk_size = 1024 * 1024  # 1MB chunks
    
    try:
        with open(destination, "wb") as buffer:
            while True:
                chunk = await upload_file.read(chunk_size)
                if not chunk:
                    break
                
                total_size += len(chunk)
                
                # ตรวจสอบขนาดไฟล์
                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail=f"ไฟล์ใหญ่เกินไป (สูงสุด {MAX_FILE_SIZE // (1024*1024)}MB)"
                    )
                
                buffer.write(chunk)
                
        return total_size
    except Exception as e:
        # ลบไฟล์ถ้าเกิดข้อผิดพลาด
        if destination.exists():
            destination.unlink()
        raise

@app.get("/health")
async def health_check():
    """ตรวจสอบสถานะของ API"""
    return {"status": "healthy", "service": "ASR Local Dialect"}

@app.post("/transcribe")
async def transcribe_api(
    file: UploadFile = File(...),
    mode: str = Form("none"),
    dialect: str = Form("isan"),
    language: Optional[str] = Form(None)
):
    """
    Transcribe audio/video file
    
    Parameters:
    - file: ไฟล์เสียงหรือวิดีโอ
    - mode: "none" | "dialect" | "standard"
    - dialect: "isan" | "kham_mueang" | "pak_tai"
    - language: initial_prompt สำหรับ Whisper
    """
    tmp_path = None
    
    try:
        # ตรวจสอบไฟล์
        if not file.filename:
            raise HTTPException(status_code=400, detail="ไม่พบชื่อไฟล์")
        
        # ตรวจสอบนามสกุลไฟล์
        valid_extensions = {'.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm', '.ogg', '.flac'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        
        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"ไฟล์ประเภท {file_ext} ไม่รองรับ รองรับเฉพาะ: {', '.join(valid_extensions)}"
            )
        
        logger.info(f"เริ่มประมวลผลไฟล์: {file.filename} ({file.content_type})")
        
        # สร้างไฟล์ชั่วคราว
        temp_dir = tempfile.gettempdir()
        tmp_path = Path(temp_dir) / f"asr_temp_{os.getpid()}_{file.filename}"
        
        # บันทึกไฟล์แบบ chunked
        file_size = await save_upload_file_chunked(file, tmp_path)
        logger.info(f"บันทึกไฟล์สำเร็จ: {file_size / (1024*1024):.2f} MB")
        
        # ตรวจสอบว่าไฟล์มีขนาดมากกว่า 0
        if file_size == 0:
            raise HTTPException(status_code=400, detail="ไฟล์ว่างเปล่า")
        
        # Transcribe
        logger.info("เริ่มการถอดเสียง...")
        segments, info = transcribe(str(tmp_path), initial_prompt=language)
        logger.info(f"ถอดเสียงสำเร็จ: {len(segments)} segments")
        
        # Post-process
        if mode in {"dialect", "standard"} and segments:
            logger.info(f"ประมวลผลโหมด: {mode}, ภาษาถิ่น: {dialect}")
            segments = apply_mode(segments, mode=mode, dialect_hint=dialect)
        
        # ดึงข้อมูลจาก info
        language_out = None
        duration_out = None
        if isinstance(info, dict):
            language_out = info.get("language")
            duration_out = info.get("duration")
        
        # สร้างผลลัพธ์
        api_result = {
            "result": {
                "language": language_out,
                "duration": duration_out,
                "segments": segments,
            },
            "files": {
                "srt": _to_srt(segments),
                "vtt": _to_vtt(segments),
            }
        }
        
        logger.info("ส่งผลลัพธ์สำเร็จ")
        return JSONResponse(api_result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาด: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"เกิดข้อผิดพลาดในการประมวลผล: {str(e)}"
        )
    finally:
        # ลบไฟล์ชั่วคราว
        if tmp_path and Path(tmp_path).exists():
            try:
                Path(tmp_path).unlink()
                logger.info("ลบไฟล์ชั่วคราวสำเร็จ")
            except Exception as e:
                logger.warning(f"ไม่สามารถลบไฟล์ชั่วคราว: {e}")

@app.get("/")
async def root():
    """API Information"""
    return {
        "service": "ASR Local Dialect — MVP",
        "version": "1.0.0",
        "endpoints": {
            "/transcribe": "POST - ถอดเสียงจากไฟล์",
            "/health": "GET - ตรวจสอบสถานะ"
        },
        "supported_formats": [".mp3", ".wav", ".m4a", ".mp4", ".mpeg", ".mpga", ".webm", ".ogg", ".flac"],
        "max_file_size_mb": MAX_FILE_SIZE // (1024 * 1024)
    }