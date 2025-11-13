import os

class ASRConfig:
    name = os.getenv("ASR_MODEL_NAME", "small")
    compute = os.getenv("ASR_COMPUTE_TYPE", "int8")
    device = os.getenv("ASR_DEVICE", "cpu")   # เพิ่มบรรทัดนี้
    force_lang = (os.getenv("FORCE_LANG", "").strip() or None)
    download_root = os.path.join(os.path.dirname(__file__), "models")
    enable_multi = os.getenv("ASR_ENABLE_MULTI", "1") == "1"
    enable_diar = os.getenv("ENABLE_DIARIZATION", "0") == "1"
    kenlm_path = os.getenv("KENLM_ARPA_PATH", "")
    alpha = float(os.getenv("RANK_ALPHA_ASR", "1.0"))
    beta  = float(os.getenv("RANK_BETA_LM", "1.2"))
    gamma = float(os.getenv("RANK_GAMMA_LEX", "0.3"))
    delta = float(os.getenv("RANK_DELTA_PEN", "0.2"))
    domain_whitelist = [w.strip() for w in os.getenv("DOMAIN_WHITELIST", "").split(",") if w.strip()]
