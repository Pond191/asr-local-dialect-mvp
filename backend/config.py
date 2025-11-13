# backend/config.py
import os

class ASRConfig:
    # =======================
    # Render-friendly setting
    # =======================
    # ใช้ tiny เพื่อลด RAM (tiny ~ 75MB)
    name = os.getenv("ASR_MODEL_NAME", "tiny")

    # compute int8 = RAM ต่ำสุด
    compute = os.getenv("ASR_COMPUTE_TYPE", "int8")

    # ใช้ CPU เท่านั้นบน Render
    device = os.getenv("ASR_DEVICE", "cpu")

    # ไม่บังคับภาษา (ให้โมเดลเดาเอง หรือส่ง initial_prompt แทน)
    force_lang = None

    # เก็บโมเดลในโฟลเดอร์ local (Render จะ cache ให้)
    download_root = os.path.join(os.path.dirname(__file__), "models")

    # ปิด multi-profiles เพื่อลดโหลดซ้ำหลายรอบ
    enable_multi = False

    # ปิด diarization (ใช้ memory เยอะ)
    enable_diar = False

    # ปิด language model (ลด RAM)
    kenlm_path = ""

    # ปิดการ ranking เพื่อประหยัด CPU
    alpha = 1.0
    beta = 0.0
    gamma = 0.0
    delta = 0.0

    domain_whitelist = []
