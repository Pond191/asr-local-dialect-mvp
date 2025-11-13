# config.py
import os

class ASRConfig:
    name = os.getenv("ASR_MODEL_NAME", "tiny")   # ใช้ tiny เท่านั้น
    compute = os.getenv("ASR_COMPUTE_TYPE", "int8")
    device = "cpu"

    force_lang = "th"
    download_root = os.path.join(os.path.dirname(__file__), "models")

    enable_multi = False          # ❌ ปิด multi profile
    enable_diar = False           # ❌ ปิด diarization
    kenlm_path = ""               # ❌ ปิด LM

    alpha = 1.0
    beta = 0.0                    # ❌ ปิด LM score
    gamma = 0.0                   # ❌ ปิด lex score
    delta = 0.0

    domain_whitelist = []
