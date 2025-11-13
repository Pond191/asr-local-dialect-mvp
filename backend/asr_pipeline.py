# backend/asr_pipeline.py
import os
from typing import Optional, List, Dict, Any
from faster_whisper import WhisperModel
from config import ASRConfig

_MODEL = None

def load_model():
    global _MODEL
    if _MODEL is None:
        os.makedirs(ASRConfig.download_root, exist_ok=True)
        _MODEL = WhisperModel(
            ASRConfig.name,
            device=ASRConfig.device,
            compute_type=ASRConfig.compute,
            download_root=ASRConfig.download_root,
        )
    return _MODEL


def transcribe(audio_path: str, initial_prompt: Optional[str] = None):
    model = load_model()

    # ใช้ profile เบาที่สุด
    params = dict(
        language=ASRConfig.force_lang,
        vad_filter=False,          # ปิด VAD (กิน RAM)
        beam_size=1,               # ลด RAM
        best_of=1,
        condition_on_previous_text=True
    )

    if initial_prompt:
        params["initial_prompt"] = initial_prompt

    segments, info = model.transcribe(audio_path, **params)

    out = []
    for s in segments:  # faster-whisper returns generator
        out.append({
            "start": float(getattr(s, "start", 0.0)),
            "end": float(getattr(s, "end", 0.0)),
            "text": (getattr(s, "text", "") or "").strip(),
        })

    return out, info
