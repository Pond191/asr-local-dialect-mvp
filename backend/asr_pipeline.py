# asr_pipeline.py — Render-safe version (low RAM, stable)
import os
from typing import List, Dict, Optional
from faster_whisper import WhisperModel
from config import ASRConfig

_MODEL = None  # เก็บโมเดลไว้โหลดครั้งเดียว


def load_model():
    """โหลดโมเดลแค่ครั้งเดียว (เหมาะสำหรับ Render RAM 512MB)"""
    global _MODEL
    if _MODEL is None:
        os.makedirs(ASRConfig.download_root, exist_ok=True)

        # บังคับรันบน CPU compute=int8 เพื่อประหยัด RAM
        _MODEL = WhisperModel(
            ASRConfig.name,                  # e.g. "small"
            device="cpu",
            compute_type="int8",
            download_root=ASRConfig.download_root,
        )
    return _MODEL


def transcribe(audio_path: str, initial_prompt: Optional[str] = None):
    """
    เวอร์ชันประหยัด RAM: ใช้ค่าที่เบาแบบสุด ไม่ทำ multi-profiles
    Render RAM 512MB ใช้ได้แบบเสถียร
    """

    model = load_model()

    params = dict(
        language=ASRConfig.force_lang or None,
        vad_filter=True,
        beam_size=3,               # เบาที่สุด แต่ยังค่อนข้างแม่น
        best_of=3,
        temperature=[0.0, 0.2],    # เบา
        condition_on_previous_text=True,
    )

    if initial_prompt:
        params["initial_prompt"] = initial_prompt

    # ทำการถอดเสียง
    segs, info = model.transcribe(audio_path, **params)
    segs = list(segs)

    # คืนค่าเป็น list ของ dict ให้ backend ใช้งานง่าย
    out = []
    for s in segs:
        out.append({
            "start": float(getattr(s, "start", 0.0)),
            "end": float(getattr(s, "end", 0.0)),
            "text": (getattr(s, "text", "") or "").strip(),
            "avg_logprob": float(getattr(s, "avg_logprob", 0.0)),
        })

    # info เช่น {"duration": xx, "language": xx}
    return out, info
