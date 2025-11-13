# backend/app.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict
import tempfile, os

from asr_pipeline import transcribe
from postprocess import apply_mode

app = FastAPI(title="ASR Local Dialect — MVP")

# CORS ที่ถูกต้องสำหรับ Render + Vercel
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Render ฟรีใช้ได้เลย
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _to_srt(segments):
    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    lines = []
    for i, s in enumerate(segments, 1):
        lines += [
            str(i),
            f"{ts(s['start'])} --> {ts(s['end'])}",
            s["text"],
            ""
        ]
    return "\n".join(lines)


def _to_vtt(segments):
    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"
    lines = ["WEBVTT", ""]
    for s in segments:
        lines += [
            f"{ts(s['start'])} --> {ts(s['end'])}",
            s["text"],
            ""
        ]
    return "\n".join(lines)


@app.post("/transcribe")
async def transcribe_api(
    file: UploadFile = File(...),
    mode: str = Form("none"),
    dialect: str = Form("isan"),
    language: Optional[str] = Form(None)
):
    # save file
    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        segments, info = transcribe(tmp_path, initial_prompt=language)

        if mode in {"dialect", "standard"}:
            segments = apply_mode(segments, mode=mode, dialect_hint=dialect)

        resp = {
            "result": {
                "language": info.get("language") if isinstance(info, dict) else None,
                "duration": info.get("duration") if isinstance(info, dict) else None,
                "segments": segments
            },
            "files": {
                "srt": _to_srt(segments),
                "vtt": _to_vtt(segments)
            }
        }
        return JSONResponse(resp)

    finally:
        try:
            os.remove(tmp_path)
        except:
            pass
