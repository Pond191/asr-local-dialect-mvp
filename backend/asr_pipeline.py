# asr_pipeline.py
import os
from typing import Optional, List, Dict
from faster_whisper import WhisperModel
from config import ASRConfig

_model = None

def load_model():
    global _model
    if _model is None:
        os.makedirs(ASRConfig.download_root, exist_ok=True)
        _model = WhisperModel(
            ASRConfig.name,
            device="cpu",
            compute_type=ASRConfig.compute,
            download_root=ASRConfig.download_root,
        )
    return _model

def transcribe(audio_path: str, initial_prompt: Optional[str] = None):
    model = load_model()

    params = dict(
        language="th",
        beam_size=1,
        best_of=1,
        vad_filter=True,
        condition_on_previous_text=True,
        temperature=0.0,
    )
    if initial_prompt:
        params["initial_prompt"] = initial_prompt

    segs, info = model.transcribe(audio_path, **params)

    # convert segment objects → dict
    output = []
    for s in segs:
        output.append({
            "start": float(s.start),
            "end": float(s.end),
            "text": (s.text or "").strip(),
        })

    return output, info
