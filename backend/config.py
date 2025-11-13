# backend/config.py
import os

class ASRConfig:
    # ชื่อโมเดล faster-whisper ที่ใช้
    # เล็ก = "tiny", "base", กลาง = "small", "medium"
    name = os.getenv("ASR_MODEL_NAME", "small")

    # ให้เบาลงหน่อยบน CPU
    ASR_COMPUTE_TYPE_DEFAULT = "int8"
    compute = os.getenv("ASR_COMPUTE_TYPE", ASR_COMPUTE_TYPE_DEFAULT)

    # ถ้าอยากบังคับภาษา (เช่น "th") ใส่ใน ENV นี้
    force_lang = (os.getenv("FORCE_LANG", "").strip() or None)

    # โฟลเดอร์เก็บโมเดลที่ดาวน์โหลดมา
    download_root = os.path.join(os.path.dirname(__file__), "models")

    # เปิด/ปิด profile หลายแบบ
    enable_multi = os.getenv("ASR_ENABLE_MULTI", "1") == "1"

    # (ตอนนี้ยังไม่ใช้ diarization)
    enable_diar = os.getenv("ENABLE_DIARIZATION", "0") == "1"

    # เส้นทางไปไฟล์ KenLM .arpa (ถ้าไม่มี ให้เว้นว่าง)
    kenlm_path = os.getenv("KENLM_ARPA_PATH", "")

    # น้ำหนักคะแนนสำหรับ ranking โปรไฟล์ต่าง ๆ
    alpha = float(os.getenv("RANK_ALPHA_ASR", "1.0"))
    beta  = float(os.getenv("RANK_BETA_LM", "1.2"))
    gamma = float(os.getenv("RANK_GAMMA_LEX", "0.3"))
    delta = float(os.getenv("RANK_DELTA_PEN", "0.2"))

    # คำสำคัญไว้บูสต์คะแนน (ถ้าอยากบอก domain พิเศษ)
    domain_whitelist = [
        w.strip()
        for w in os.getenv("DOMAIN_WHITELIST", "").split(",")
        if w.strip()
    ]
