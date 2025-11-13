import os

class ASRConfig:
    # ชื่อโมเดล (เคยใช้ small แล้วรันบนเครื่องคุณได้)
    name = os.getenv("ASR_MODEL_NAME", "small")

    # ประเภท compute ของ faster-whisper (int8 ประหยัดแรม)
    compute = os.getenv("ASR_COMPUTE_TYPE", "int8")

    # รันบน CPU
    device = os.getenv("ASR_DEVICE", "cpu")

    # บังคับภาษา เช่น "th" หรือปล่อยว่างให้เดาเอง
    force_lang = (os.getenv("FORCE_LANG", "").strip() or None)

    # โฟลเดอร์เก็บโมเดล
    download_root = os.path.join(os.path.dirname(__file__), "models")

    # ลองหลายโปรไฟล์หรือไม่
    enable_multi = os.getenv("ASR_ENABLE_MULTI", "1") == "1"

    # ตอนนี้ยังไม่ใช้ diarization แต่เผื่อไว้
    enable_diar = os.getenv("ENABLE_DIARIZATION", "0") == "1"

    # ถ้าไม่มี LM ก็ปล่อยว่างได้
    kenlm_path = os.getenv("KENLM_ARPA_PATH", "")

    # น้ำหนักรวมคะแนน
    alpha = float(os.getenv("RANK_ALPHA_ASR", "1.0"))
    beta  = float(os.getenv("RANK_BETA_LM", "1.2"))
    gamma = float(os.getenv("RANK_GAMMA_LEX", "0.3"))
    delta = float(os.getenv("RANK_DELTA_PEN", "0.2"))

    # คำเฉพาะโดเมน (ไม่มีก็ปล่อยว่างได้)
    domain_whitelist = [
        w.strip()
        for w in os.getenv("DOMAIN_WHITELIST", "").split(",")
        if w.strip()
    ]
