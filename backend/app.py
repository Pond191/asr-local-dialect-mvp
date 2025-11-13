# asr-local-dialect-mvp/backend/app.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import tempfile, os

from asr_pipeline import transcribe      # คืนค่า (segments, info)  หรือ list ของ segment objects
from postprocess import apply_mode       # dialect/standard/none

app = FastAPI(title="ASR Local Dialect — MVP")

# CORS เผื่อ dev ข้ามพอร์ต
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

def _to_srt(segments: List[Dict]) -> str:
    def ts(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"
    lines = []
    for i, s in enumerate(segments, 1):
        lines += [str(i), f"{ts(s['start'])} --> {ts(s['end'])}", s.get("text", ""), ""]
    return "\n".join(lines)

def _to_vtt(segments: List[Dict]) -> str:
    def ts(t):
        h = int(t // 3600); m = int((t % 3600) // 60); s = int(t % 60); ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"
    lines = ["WEBVTT", ""]
    for s in segments:
        lines += [f"{ts(s['start'])} --> {ts(s['end'])}", s.get("text", ""), ""]
    return "\n".join(lines)

def _seg_to_dict(s: Any) -> Dict[str, Any]:
    """รองรับทั้ง faster-whisper Segment objects และ dict ที่มีคีย์ start/end/text"""
    if isinstance(s, dict):
        start = float(s.get("start", 0.0) or 0.0)
        end   = float(s.get("end",   0.0) or 0.0)
        text  = (s.get("text", "") or "").strip()
    else:
        # segment object: มีแอททริบิวต์ start/end/text
        start = float(getattr(s, "start", 0.0) or 0.0)
        end   = float(getattr(s, "end",   0.0) or 0.0)
        text  = (getattr(s, "text", "") or "").strip()
    return {"start": start, "end": end, "text": text}

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
        # เรียก pipeline -> บางเวอร์ชันคืน (segments, info) บางเวอร์ชันคืน dict
        result = transcribe(tmp_path, initial_prompt=language)

        if isinstance(result, tuple):
            segs, info = result
            segments = [_seg_to_dict(s) for s in (segs or [])]
            language_out = info.get("language") if isinstance(info, dict) else None
            duration_out = info.get("duration") if isinstance(info, dict) else None
        elif isinstance(result, dict):
            raw_segments = result.get("segments", []) or []
            segments = [_seg_to_dict(s) for s in raw_segments]
            language_out = result.get("language")
            duration_out = result.get("duration")
        else:
            segments = []
            language_out = None
            duration_out = None

        # post-process ตามโหมด
        if mode in {"dialect", "standard"} and segments:
            segments = apply_mode(segments, mode=mode, dialect_hint=dialect)

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
