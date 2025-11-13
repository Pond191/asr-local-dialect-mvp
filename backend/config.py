import os
import os.path as op

class ASRConfig:
    # ใช้รุ่น tiny เพื่อลดขนาดโมเดลให้เหมาะกับ Render ฟรี
    name = os.getenv("ASR_MODEL_NAME", "tiny")

    # int8 = ประหยัดแรมสุดสำหรับ CPU
    compute = os.getenv("ASR_COMPUTE_TYPE", "int8")

    # บังคับให้รันบน CPU เสมอ
    device = os.getenv("ASR_DEVICE", "cpu")

    # บังคับภาษา (ใช้ th สำหรับไทย/ภาษาถิ่น)
    force_lang = (os.getenv("FORCE_LANG", "th").strip() or None)

    # โฟลเดอร์เก็บโมเดลบนดิสก์ของ Render
    download_root = op.join(op.dirname(__file__), "models")

    # ปิดโหมดลองหลาย profile เพื่อไม่ให้รันซ้ำหลายรอบ
    enable_multi = False

    # ปิด diarization / LM เพื่อประหยัด RAM
    enable_diar = False
    kenlm_path = ""

    # ตัว ranking ด้านล่างไม่ได้ใช้แล้ว แต่คงไว้เฉย ๆ
    alpha = 1.0
    beta  = 0.0
    gamma = 0.0
    delta = 0.0
    domain_whitelist = []
