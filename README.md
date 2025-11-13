# ASR Local Dialect — MVP (พร้อมใช้งาน)

## โครงสร้าง
- `backend/` — FastAPI + faster-whisper + (option) pyannote diarization
- `frontend/` — Next.js หน้าเดียวอัปโหลดไฟล์และดูผล

## วิธีรันเร็วที่สุด (แยก 2 เทอร์มินัล)
### 1) Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# ติดตั้ง ffmpeg ในระบบก่อน (Linux: apt, macOS: brew, Windows: choco/scoop)
cp .env.example .env
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```

### 2) Frontend
```bash
cd frontend
npm i
export NEXT_PUBLIC_API_URL=http://localhost:8000
npm run dev
```

เปิด `http://localhost:3000` แล้วทดสอบอัปโหลดไฟล์เสียง
