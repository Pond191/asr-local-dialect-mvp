ASR Local Dialect — Patch v3
- backend: config.py, asr_pipeline.py (multi-profile), postprocess.py (phrase+lex+normalize), requirements.txt
- frontend: proxy route + minimal QA UI (แก้ข้อความ, ค้นหา/แทนที่, ดาวน์โหลด SRT/VTT/JSON)

ติดตั้ง:
- คัดลอกไฟล์ backend/* ไปวางในโปรเจกต์ backend
- คัดลอก frontend/app/* ไปวางทับของเดิม
- ตั้งค่า ENV (ตัวอย่าง):
  set CUDA_VISIBLE_DEVICES=-1
  set CT2_USE_CPU=1
  set ASR_MODEL_NAME=small
  set ASR_COMPUTE_TYPE=int8
  set FORCE_LANG=th
  set ASR_ENABLE_MULTI=1
  set NEXT_PUBLIC_API_URL=http://127.0.0.1:8000

ถ้ามี KenLM: set KENLM_ARPA_PATH=... (ถ้าไม่ตั้งจะข้าม LM อัตโนมัติ)
