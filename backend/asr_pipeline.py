import os
from typing import List, Dict, Optional, Tuple
from faster_whisper import WhisperModel

from config import ASRConfig

_MODEL: Optional[WhisperModel] = None


def load_model() -> WhisperModel:
    """โหลดโมเดล tiny แค่ครั้งเดียวแบบ lazy singleton"""
    global _MODEL
    if _MODEL is not None:
        return _MODEL

    os.makedirs(ASRConfig.download_root, exist_ok=True)

    _MODEL = WhisperModel(
        ASRConfig.name,               # ควรเป็น "tiny"
        device=ASRConfig.device,      # "cpu"
        compute_type=ASRConfig.compute,  # "int8"
        download_root=ASRConfig.download_root,
    )
    return _MODEL


def transcribe(
    audio_path: str,
    initial_prompt: Optional[str] = None,
) -> Tuple[List[Dict], Dict]:
    """
    ถอดเสียงแบบง่ายที่สุด เพื่อลดการใช้ RAM:
    - เรียก model.transcribe แค่ครั้งเดียว
    - ไม่ใช้ LM, ไม่วนหลาย profile
    """
    model = load_model()

    params = dict(
        language=ASRConfig.force_lang,          # "th"
        vad_filter=False,                       # ปิด VAD เพื่อลดโมเดลเพิ่ม
        beam_size=5,
        best_of=5,
        condition_on_previous_text=True,
    )
    if initial_prompt:
        params["initial_prompt"] = initial_prompt

    segments_iter, info = model.transcribe(audio_path, **params)

    segments_out: List[Dict] = []
    for s in segments_iter:
        segments_out.append(
            {
                "start": float(getattr(s, "start", 0.0) or 0.0),
                "end": float(getattr(s, "end", 0.0) or 0.0),
                "text": (getattr(s, "text", "") or "").strip(),
                "avg_logprob": float(getattr(s, "avg_logprob", 0.0) or 0.0),
            }
        )

    # ให้ตรงกับ app.py ที่คาดว่า transcribe(...) คืน (segments, info)
    return segments_out, info
