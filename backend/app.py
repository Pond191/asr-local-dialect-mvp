# asr-local-dialect-mvp/backend/app.py
from typing import Optional, List, Dict, Any
import os
import tempfile

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from asr_pipeline import transcribe      # คืนค่า (segments: list[dict], info: dict)
from postprocess import apply_mode       # dialect/standard/none

app = FastAPI(title="ASR Local Dialect — MVP")

# --- CORS สำหรับให้ Vercel / localhost เรียกใช้ได้ ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://asr-local-dialect-mvp.vercel.app",
        "https://asr-local-dialect-mvp.onrender.com",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- helper แปลง segments เป็น SRT/VTT + dict ปลอดภัย ---
def _to_srt(segments: List[Dict[str, Any]]) -> str:
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


def _to_vtt(segments: List[Dict[str, Any]]) -> str:
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


def _seg_to_dict(s: Any) -> Dict[str, Any]:
    """
    เผื่อในอนาคต transcribe คืน object แทน dict
    ตอนนี้ใน asr_pipeline เราคืน dict อยู่แล้ว ฟังก์ชันนี้เลยแทบไม่ทำอะไรเพิ่ม
    """
    if isinstance(s, dict):
        start = float(s.get("start", 0.0) or 0.0)
        end = float(s.get("end", 0.0) or 0.0)
        text = (s.get("text", "") or "").strip()
    else:
        start = float(getattr(s, "start", 0.0) or 0.0)
        end = float(getattr(s, "end", 0.0) or 0.0)
        text = (getattr(s, "text", "") or "").strip()

    return {"start": start, "end": end, "text": text}


# --- endpoint หลัก ---
@app.post("/transcribe")
async def transcribe_api(
    file: UploadFile = File(...),
    mode: str = Form("standard"),         # "none" | "dialect" | "standard"
    dialect: str = Form("isan"),          # "isan" | "kham_mueang" | "pak_tai"
    language: Optional[str] = Form(None), # ส่งเข้า initial_prompt (ช่วยคอนเท็กซ์ภาษา/สำเนียง)
):
    # อ่านข้อมูลไฟล์เข้ามาก่อน
    data = await file.read()

    # กันไฟล์ใหญ่เกินไป (เช่น > 50 MB) บน Render ฟรี
    if len(data) > 50 * 1024 * 1024:
        return JSONResponse(
            {
                "error": "ไฟล์มีขนาดใหญ่เกิน 50 MB (ข้อจำกัดของเซิร์ฟเวอร์ทดลอง) "
                         "กรุณาตัดไฟล์ให้สั้นลงก่อนอัปโหลด"
            },
            status_code=413,
        )

    # เซฟไฟล์ชั่วคราว
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(file.filename or "")[1]
    ) as tmp:
        tmp.write(data)
        tmp_path = tmp.name

    try:
        # เรียก pipeline (ตอนนี้ asr_pipeline.transcribe คืน list[dict], dict)
        segs, info = transcribe(tmp_path, initial_prompt=language)

        segments = [_seg_to_dict(s) for s in (segs or [])]

        # post-process ตามโหมด
        if mode in {"dialect", "standard"} and segments:
            segments = apply_mode(segments, mode=mode, dialect_hint=dialect)

        language_out = None
        duration_out = None
        if isinstance(info, dict):
            language_out = info.get("language")
            duration_out = info.get("duration")

        api_result = {
            "result": {
                "language": language_out,
                "duration": duration_out,
                "segments": segments,
            },
            "files": {
                "srt": _to_srt(segments),
                "vtt": _to_vtt(segments),
            },
        }
        return JSONResponse(api_result)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
