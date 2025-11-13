from typing import List, Dict
import json, os, re
from pythainlp.util import normalize
from pythainlp import word_tokenize, sent_tokenize

_BASE_DIR = os.path.dirname(__file__)
_LEX_DIR = os.path.join(_BASE_DIR, "lexicons")
_PHRASE_FILE = os.path.join(_BASE_DIR, "phrase_maps.json")

_LEX_CACHE: Dict[str, Dict[str, str]] = {}
_PHRASE_CACHE: Dict[str, List[List[str]]] = {}
_PHRASE_MTIME: float = -1.0

def _load_lex(name: str) -> Dict[str, str]:
    path = os.path.join(_LEX_DIR, name)
    if not os.path.exists(path):
        return {}
    if name not in _LEX_CACHE:
        with open(path, "r", encoding="utf-8") as f:
            _LEX_CACHE[name] = json.load(f)
    return _LEX_CACHE[name]

def _default_phrase_maps() -> Dict[str, List[List[str]]]:
    return {
        "isan": [
            ["มือละคำ", "วันละคำ"],
            ["มื่อนี่", "วันนี้"],
            ["กินเข่าหรือยัง", "กินข้าวหรือยัง"],
            ["เว้าซื่อๆ", "พูดตามตรง"],
            ["บ่เป็นหยังดอก", "ไม่เป็นไรหรอก"],
            ["ย้านเจ้าหักคนอื่น", "กลัวเธอไปชอบคนอื่น"],
            ["ไปไสมาไส", "ไปไหนมาไหน"],
        ],
        "kham_mueang": [
            ["ไปแอ่วกั๋น", "ไปเที่ยวกัน"],
            ["ลำแต๊ๆ", "อร่อยจริงๆ"],
            ["ปิ๊กเฮือนก่อนเน้อ", "กลับบ้านก่อนนะ"],
        ],
        "pak_tai": [
            ["หรอยจังหู", "อร่อยมาก"],
            ["ตะไปหลบก่อนนิ", "จะกลับก่อนนะ"],
            ["พรือมั้งเห้อ", "เป็นอย่างไรบ้างนะ"],
        ],
    }

def _load_phrase_maps(force: bool=False) -> Dict[str, List[List[str]]]:
    global _PHRASE_CACHE, _PHRASE_MTIME
    mtime = os.path.getmtime(_PHRASE_FILE) if os.path.exists(_PHRASE_FILE) else -1.0
    need_reload = force or not _PHRASE_CACHE or (mtime >= 0 and mtime != _PHRASE_MTIME)
    if not need_reload:
        return _PHRASE_CACHE
    try:
        if mtime >= 0:
            with open(_PHRASE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                raise ValueError("phrase_maps.json is not a dict")
            _PHRASE_CACHE = data
            _PHRASE_MTIME = mtime
        else:
            _PHRASE_CACHE = _default_phrase_maps()
            _PHRASE_MTIME = -1.0
    except Exception:
        _PHRASE_CACHE = _default_phrase_maps()
        _PHRASE_MTIME = -1.0
    return _PHRASE_CACHE

def prettify_thai(text: str) -> str:
    txt = normalize(text)
    txt = re.sub(r"(.)\1{3,}", r"\1\1", txt)
    txt = re.sub(r",(?=\S)", ", ", txt)
    txt = re.sub(r"\s{2,}", " ", txt).strip()
    return txt

def _normalize_isan_noise(text: str) -> str:
    t = text
    t = re.sub(r"แปลว[\s่ะะ]*", "แปลว่า", t)
    t = re.sub(r"(ก[่า]ว|กาว)\s*ว่า+", "บอกว่า", t)
    t = re.sub(r"(ว่า)(\s*ว่า)+", r"\1", t)
    t = re.sub(r"(บอก)\s*\1", r"\1", t)
    t = re.sub(r"ต้มต้ม", "ตรงๆ", t)
    t = re.sub(r"\s{2,}", " ", t).strip()
    return t

def _apply_phrases(text: str, dialect: str, mode: str) -> str:
    if mode != "standard":
        return text
    maps = _load_phrase_maps().get(dialect, [])
    for pair in maps:
        if not isinstance(pair, (list, tuple)) or len(pair) != 2:
            continue
        src, dst = pair
        if not src:
            continue
        text = text.replace(src, dst)
    return text

def keep_dialect(text: str) -> str:
    return prettify_thai(text)

def dialect_to_thai(text: str, dialect: str = "isan") -> str:
    text = prettify_thai(text)
    text = _apply_phrases(text, dialect, mode="standard")
    lex = _load_lex(f"{dialect}.json")
    if lex:
        tokens = word_tokenize(text, engine="newmm")
        text = "".join(lex.get(tok, tok) for tok in tokens)
    if dialect == "isan":
        text = _normalize_isan_noise(text)
    return text

def apply_mode(segments: List[Dict], mode: str, dialect_hint: str = "isan") -> List[Dict]:
    out = []
    for s in segments:
        txt = s.get("text", "")
        if mode == "dialect":
            new_txt = keep_dialect(txt)
        elif mode == "standard":
            new_txt = dialect_to_thai(txt, dialect=dialect_hint)
        else:
            new_txt = txt
        out = out + [{**s, "text": prettify_thai(new_txt)}]
    return out
