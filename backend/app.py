# asr-local-dialect-mvp/backend/app.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
import tempfile, os

from asr_pipeline import transcribe      # คืนค่า (segments: List[Dict], info)
from postprocess import apply_mode       # dialect/standard/none

app = FastAPI(title="ASR Local Dialect — MVP")

# CORS แบบง่าย ๆ สำหรับใช้บนเครื่องตัวเอง หรือ dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _to_srt(segments: List[Dict]) -> str:
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

@app.post("/transcribe")
async def transcribe_api(
    file: UploadFile = File(...),
    mode: str = Form("none"),            # "none" | "dialect" | "standard"
    dialect: str = Form("isan"),         # "isan" | "kham_mueang" | "pak_tai"
    language: Optional[str] = Form(None) # ส่งเข้า initial_prompt (ช่วยคอนเท็กซ์ภาษา/สำเนียง)
):
    # เซฟไฟล์ชั่วคราว
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or "")[1]) as tmp:
        data = await file.read()
        tmp.write(data)
        tmp_path = tmp.name

    try:
        segments, info = transcribe(tmp_path, initial_prompt=language)

        # post-process ตามโหมด (segments เป็น list ของ dict แล้ว)
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
            }
        }
        return JSONResponse(api_result)
    finally:
        try:
            os.remove(tmp_path)
        except Exception:
            pass
