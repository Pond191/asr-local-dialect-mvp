import os
import logging
from typing import List, Dict, Optional, Tuple, Any
from faster_whisper import WhisperModel
from config import ASRConfig

logger = logging.getLogger(__name__)

_MODEL = None
_LM = None

def _maybe_load_lm():
    """โหลด KenLM language model ถ้ามี"""
    global _LM
    if _LM is not None:
        return _LM
    
    p = ASRConfig.kenlm_path
    if not p:
        logger.info("ไม่ได้ตั้งค่า KenLM path")
        _LM = None
        return None
    
    try:
        import kenlm
        _LM = kenlm.Model(p)
        logger.info(f"โหลด KenLM สำเร็จจาก {p}")
    except ImportError:
        logger.warning("ไม่พบ kenlm library, ข้ามการใช้งาน language model")
        _LM = None
    except Exception as e:
        logger.warning(f"ไม่สามารถโหลด KenLM: {e}")
        _LM = None
    
    return _LM

def load_model() -> WhisperModel:
    """โหลด Whisper model (singleton pattern)"""
    global _MODEL
    if _MODEL is None:
        try:
            os.makedirs(ASRConfig.download_root, exist_ok=True)
            logger.info(f"กำลังโหลดโมเดล {ASRConfig.name} บน {ASRConfig.device}...")
            
            _MODEL = WhisperModel(
                ASRConfig.name,
                device=ASRConfig.device,
                compute_type=ASRConfig.compute,
                download_root=ASRConfig.download_root,
                num_workers=4,  # เพิ่มจำนวน workers สำหรับไฟล์ใหญ่
            )
            
            logger.info("โหลดโมเดลสำเร็จ")
        except Exception as e:
            logger.error(f"ไม่สามารถโหลดโมเดลได้: {e}")
            raise
    
    return _MODEL

def _profiles() -> List[Dict[str, Any]]:
    """สร้าง profile สำหรับการถอดเสียง"""
    if not ASRConfig.enable_multi:
        return [dict(
            language=ASRConfig.force_lang,
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.5,
                min_speech_duration_ms=250,
                max_speech_duration_s=float('inf'),
                min_silence_duration_ms=2000,
                speech_pad_ms=400,
            ),
            beam_size=5,
            best_of=5,
            temperature=[0.0, 0.2],
            condition_on_previous_text=True,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        )]
    
    # หลาย profile สำหรับความแม่นยำสูงสุด
    return [
        # Profile 1: ภาษาไทยแบบเข้มงวด
        dict(
            language=ASRConfig.force_lang or "th",
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.5,
                min_speech_duration_ms=250,
                max_speech_duration_s=float('inf'),
                min_silence_duration_ms=2000,
                speech_pad_ms=400,
            ),
            beam_size=5,
            best_of=5,
            temperature=[0.0, 0.2],
            condition_on_previous_text=True,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        ),
        # Profile 2: ยืดหยุ่นกว่า
        dict(
            language=None,
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.4,
                min_speech_duration_ms=200,
                max_speech_duration_s=float('inf'),
                min_silence_duration_ms=1500,
                speech_pad_ms=300,
            ),
            beam_size=5,
            best_of=5,
            temperature=[0.0, 0.2, 0.4],
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        ),
        # Profile 3: สำหรับเสียงที่ยากมาก
        dict(
            language=ASRConfig.force_lang,
            vad_filter=True,
            vad_parameters=dict(
                threshold=0.3,
                min_speech_duration_ms=150,
                max_speech_duration_s=float('inf'),
                min_silence_duration_ms=1000,
                speech_pad_ms=200,
            ),
            beam_size=3,
            best_of=3,
            temperature=[0.2, 0.4],
            condition_on_previous_text=False,
            compression_ratio_threshold=2.4,
            log_prob_threshold=-1.0,
            no_speech_threshold=0.6,
        ),
    ]

def _score_asr(segs) -> float:
    """คำนวณคะแนน ASR จาก average log probability"""
    vals = []
    for s in segs:
        al = getattr(s, "avg_logprob", None)
        if al is not None:
            vals.append(float(al))
    
    if not vals:
        return -999.0
    
    return sum(vals) / len(vals)

def _lm_score(text: str) -> float:
    """คำนวณคะแนนจาก language model"""
    lm = _maybe_load_lm()
    if lm is None:
        return 0.0
    
    try:
        return lm.score(text, bos=True, eos=True)
    except Exception as e:
        logger.warning(f"ไม่สามารถคำนวณ LM score: {e}")
        return 0.0

def _lex_bonus(text: str) -> float:
    """คำนวณคะแนนโบนัสจากคำในพจนานุกรมโดเมน"""
    b = 0.0
    for w in ASRConfig.domain_whitelist:
        if w and w in text:
            b += 0.5
    return b

def transcribe(
    audio_path: str, 
    initial_prompt: Optional[str] = None
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    ถอดเสียงจากไฟล์เสียง/วิดีโอ
    
    Args:
        audio_path: path ของไฟล์
        initial_prompt: คำใบ้ภาษาสำหรับโมเดล
    
    Returns:
        (segments, info) โดย segments เป็น list ของ dict
        [{start, end, text, avg_logprob}, ...]
    """
    try:
        model = load_model()
    except Exception as e:
        logger.error(f"ไม่สามารถโหลดโมเดล: {e}")
        raise
    
    best = None
    best_score = -1e9
    best_info = None
    
    profiles = _profiles()
    logger.info(f"จะทดลอง {len(profiles)} profiles")
    
    for idx, prof in enumerate(profiles):
        try:
            logger.info(f"กำลังลอง profile {idx + 1}/{len(profiles)}")
            
            params = dict(prof)
            if initial_prompt:
                params["initial_prompt"] = initial_prompt
            
            # ถอดเสียง
            segs, info = model.transcribe(audio_path, **params)
            segs = list(segs)
            
            if not segs:
                logger.warning(f"Profile {idx + 1} ไม่พบ segments")
                continue
            
            # คำนวณคะแนน
            asr = _score_asr(segs)
            text = " ".join([(s.text or "").strip() for s in segs])
            
            score = (
                ASRConfig.alpha * asr
                + ASRConfig.beta * _lm_score(text)
                + ASRConfig.gamma * _lex_bonus(text)
            )
            
            logger.info(f"Profile {idx + 1} score: {score:.4f} (ASR: {asr:.4f})")
            
            if score > best_score:
                best, best_score, best_info = segs, score, info
                logger.info(f"Profile {idx + 1} เป็นผลลัพธ์ที่ดีที่สุดตอนนี้")
        
        except Exception as e:
            logger.error(f"Profile {idx + 1} เกิดข้อผิดพลาด: {e}")
            continue
    
    if best is None:
        raise ValueError("ไม่สามารถถอดเสียงได้จากทุก profiles กรุณาตรวจสอบไฟล์")
    
    # แปลง segments เป็น dict
    out: List[Dict[str, Any]] = []
    for s in best:
        out.append({
            "start": float(getattr(s, "start", 0.0) or 0.0),
            "end": float(getattr(s, "end", 0.0) or 0.0),
            "text": (getattr(s, "text", "") or "").strip(),
            "avg_logprob": float(getattr(s, "avg_logprob", 0.0) or 0.0),
        })
    
    logger.info(f"ถอดเสียงสำเร็จ: {len(out)} segments, score: {best_score:.4f}")
    
    return out, best_info