# asr-local-dialect-mvp/backend/app.py

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional, List, Dict, Any
import tempfile, os

from asr_pipeline import transcribe
from postprocess import apply_mode

app = FastAPI(title="ASR Local Dialect — MVP")

# ======================================================
# 1) เพิ่ม CORS ให้ครบ
# ======================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",   # << ใช้ * ไปเลยสำหรับ Render + Vercel
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 2) ฟังก์ชันแปลง segment → dict  (จำเป็นมาก!)
# ======================================================
def _seg_to_dict(s: Any) -> Dict[str, Any]:
    if isinstance(s, dict):
        start = float(s.get("start", 0.0) or 0.0)
        end   = float(s.get("end",   0.0) or 0.0)
        text  = (s.get("text", "") or "").strip()
    else:
        start = float(getattr(s, "start", 0.0) or 0.0)
        end   = float(getattr(s, "end",   0.0) or 0.0)
        text  = (getattr(s, "text", "") or "").strip()
    return {"start": start, "end": end, "text": text}

# ======================================================
# 3) ฟังก์ชันสร้าง SRT
# ======================================================
def _to_srt(segments):
    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02},{ms:03}"

    out = []
    for i, seg in enumerate(segments, 1):
        out.append(str(i))
        out.append(f"{ts(seg['start'])} --> {ts(seg['end'])}")
        out.append(seg["text"])
        out.append("")
    return "\n".join(out)

# ======================================================
# 4) ฟังก์ชันสร้าง VTT
# ======================================================
def _to_vtt(segments):
    def ts(t):
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int((t - int(t)) * 1000)
        return f"{h:02}:{m:02}:{s:02}.{ms:03}"

    out = ["WEBVTT", ""]
    for seg in segments:
        out.append(f"{ts(seg['start'])} --> {ts(seg['end'])}")
        out.append(seg["text"])
        out.append("")
    return "\n".join(out)

# ======================================================
# 5) MAIN ENDPOINT
# ======================================================
@app.post("/transcribe")
async def transcribe_api(
    file: UploadFile = File(...),
    mode: str = Form("none"),
    dialect: str = Form("isan"),
    language: Optional[str] = Form(None)
):
    with tempfile.NamedTemporaryFile(delete=False,
                                     suffix=os.path.splitext(file.filename or "")[1]) as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    try:
        result = transcribe(tmp_path, initial_prompt=language)

        if isinstance(result, tuple):
            segs, info = result
            segments = [_seg_to_dict(s) for s in segs]
            language_out = info.get("language") if isinstance(info, dict) else None
            duration_out = info.get("duration") if isinstance(info, dict) else None
        else:
            segments = [_seg_to_dict(s) for s in result.get("segments", [])]
            language_out = result.get("language")
            duration_out = result.get("duration")

        if mode in {"dialect", "standard"}:
            segments = apply_mode(segments, mode=mode, dialect_hint=dialect)

        return JSONResponse({
            "result": {
                "language": language_out,
                "duration": duration_out,
                "segments": segments
            },
            "files": {
                "srt": _to_srt(segments),
                "vtt": _to_vtt(segments)
            }
        })

    finally:
        try:
            os.remove(tmp_path)
        except:
            pass
