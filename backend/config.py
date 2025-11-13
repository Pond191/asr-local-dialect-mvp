# backend/config.py
import os

class ASRConfig:
    # ----------- MODEL ----------
    name = "Systran/faster-whisper-tiny"   # เล็กที่สุด
    compute = "int8"                       # เบาที่สุด
    device = "cpu"                         # Render ไม่มีกระทิง GPU

    # ----------- SIMPLE SETTINGS ----------
    # เราจะยกเลิกระบบ multi-profile เพราะกิน RAM มาก
    enable_multi = False
    force_lang = None

    # ----------- DOWNLOAD ----------
    download_root = os.path.join(os.path.dirname(__file__), "models")

    # ----------- LM / WHITELIST (ปิดทั้งหมด) ----------
    kenlm_path = ""
    domain_whitelist = []

    # ปิดระบบการให้คะแนนขั้นสูงทั้งหมด (ลด RAM)
    alpha = 1.0
    beta  = 0.0
    gamma = 0.0
    delta = 0.0
