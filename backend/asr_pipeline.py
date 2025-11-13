# backend/asr_pipeline.py
import os
from typing import List, Dict, Optional
from faster_whisper import WhisperModel
from config import ASRConfig

_MODEL = None
_LM = None

def _maybe_load_lm():
    global _LM
    if _LM is not None:
        return _LM
    p = ASRConfig.kenlm_path
    if not p:
        _LM = None
        return None
    try:
        import kenlm  # optional
        _LM = kenlm.Model(p)
    except Exception:
        _LM = None
    return _LM

def load_model():
    global _MODEL
    if _MODEL is None:
        os.makedirs(ASRConfig.download_root, exist_ok=True)
        # เวอร์ชันเดิม: ไม่ใส่ device พิเศษ ปล่อยให้ faster-whisper เลือกเอง
        _MODEL = WhisperModel(
            ASRConfig.name,
            compute_type=ASRConfig.compute,
            download_root=ASRConfig.download_root,
        )
    return _MODEL

def _profiles() -> List[Dict]:
    if not ASRConfig.enable_multi:
        return [
            dict(
                language=ASRConfig.force_lang,
                vad_filter=True,
                beam_size=5,
                best_of=5,
                temperature=[0.0, 0.2],
                condition_on_previous_text=True,
            )
        ]
    return [
        dict(
            language=ASRConfig.force_lang or "th",
            vad_filter=True,
            beam_size=5,
            best_of=5,
            temperature=[0.0, 0.2],
            condition_on_previous_text=True,
        ),
        dict(
            language=None,
            vad_filter=True,
            beam_size=5,
            best_of=5,
            temperature=[0.0, 0.2, 0.4],
            condition_on_previous_text=False,
        ),
        dict(
            language=ASRConfig.force_lang,
            vad_filter=True,
            beam_size=3,
            best_of=3,
            temperature=[0.2, 0.4],
            condition_on_previous_text=False,
        ),
    ]

def _score_asr(segs) -> float:
    vals = []
    for s in segs:
        al = getattr(s, "avg_logprob", None)
        if al is not None:
            vals.append(float(al))
    return sum(vals) / len(vals) if vals else -999.0

def _lm_score(text: str) -> float:
    lm = _maybe_load_lm()
    if lm is None:
        return 0.0
    try:
        return lm.score(text, bos=True, eos=True)
    except Exception:
        return 0.0

def _lex_bonus(text: str) -> float:
    b = 0.0
    for w in ASRConfig.domain_whitelist:
        if w and w in text:
            b += 0.5
    return b

def transcribe(audio_path: str, initial_prompt: Optional[str] = None):
    """
    คืนค่า: (segments_list, best_info)
    segments_list เป็น list ของ dict: {start, end, text, avg_logprob}
    """
    model = load_model()
    best = None
    best_score = -1e9
    best_info = None

    for prof in _profiles():
        params = dict(prof)
        if initial_prompt:
            params["initial_prompt"] = initial_prompt

        segs, info = model.transcribe(audio_path, **params)
        segs = list(segs)

        asr = _score_asr(segs)
        text = " ".join([(s.text or "").strip() for s in segs])
        score = (
            ASRConfig.alpha * asr
            + ASRConfig.beta * _lm_score(text)
            + ASRConfig.gamma * _lex_bonus(text)
        )

        if score > best_score:
            best, best_score, best_info = segs, score, info

    out = []
    for s in best or []:
        out.append(
            {
                "start": float(getattr(s, "start", 0.0) or 0.0),
                "end": float(getattr(s, "end", 0.0) or 0.0),
                "text": (getattr(s, "text", "") or "").strip(),
                "avg_logprob": float(getattr(s, "avg_logprob", 0.0) or 0.0),
            }
        )

    return out, best_info
