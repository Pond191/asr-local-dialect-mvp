# backend/app.py
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any, List
import tempfile, os

from asr_pipeline import transcribe


app = FastAPI(title="ASR Local Dialect — MVP")

# ========================
# CORS สำหรับ Render + Vercel
# ========================
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


# ---------- Helper ----------
def _ts_hhmmss(t: float) -> str:
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    return f"{h:01}:{m:02}:{s:02}"


def _to_srt(segments: List[Dict]) -> str:
    lines = []
    for i, s in enumerate(segments, start=1):
        lines.append(str(i))
        lines.append(f"{_ts_hhmmss(s['start'])},000 --> {_ts_hhmmss(s['end'])},000")
        lines.append(s["text"])
        lines.append("")
    return "\n".join(lines)


def _to_vtt(segments: List[Dict]) -> str:
    lines = ["WEBVTT", ""]
    for s in segments:
        lines.append(f"{_ts_hhmmss(s['start'])}.000 --> {_ts_hhmmss(s['end'])}.000")
        lines.append(s["text"])
        lines.append("")
    return "\n".join(lines)


# ---------- API ----------
@app.post("/transcribe")
async def transcribe_api(
    file: UploadFile = File(...),
    mode: str = Form("none"),
    dialect: str = Form("isan"),
    language: Optional[str] = Form(None),
):

    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
        raw = await file.read()
        tmp.write(raw)
        audio_path = tmp.name

    try:
        # call pipeline
        segments, info = transcribe(audio_path, initial_prompt=language)

        result = {
            "result": {
                "language": info.get("language") if isinstance(info, dict) else None,
                "duration": info.get("duration") if isinstance(info, dict) else None,
                "segments": segments,
            },
            "files": {
                "srt": _to_srt(segments),
                "vtt": _to_vtt(segments),
            }
        }
        return JSONResponse(result)

    finally:
        try: os.remove(audio_path)
        except: pass
