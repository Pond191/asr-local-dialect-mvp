@echo on
title ASR Local Dialect - Backend
echo ================================
echo   START ASR LOCAL DIALECT API
echo ================================
echo.

REM ตรวจว่ามี app.py ไหม
if not exist app.py (
    echo [ERROR] ไม่พบ app.py ในโฟลเดอร์นี้
    pause
    exit /b
)

REM ตรวจ python
where python
if %errorlevel% neq 0 (
    echo [ERROR] ไม่พบคำสั่ง python กรุณาติดตั้ง Python 3.8+
    pause
    exit /b
)

REM ตรวจ / สร้าง venv
if not exist venv (
    echo [INFO] สร้าง virtual environment...
    python -m venv venv
)

echo [INFO] เปิดใช้งาน virtual environment...
call venv\Scripts\activate

echo [INFO] แสดงเวอร์ชัน Python ปัจจุบัน:
python --version

echo [INFO] ติดตั้ง dependencies จาก requirements.txt...
pip install -r requirements.txt

REM สร้างโฟลเดอร์ models ถ้ายังไม่มี
if not exist models (
    echo [INFO] สร้างโฟลเดอร์ models...
    mkdir models
)

REM สร้างไฟล์ .env ถ้ายังไม่มี
if not exist .env (
    echo [INFO] ไม่พบ .env กำลังสร้างใหม่...
    (
        echo ASR_MODEL_NAME=small
        echo ASR_COMPUTE_TYPE=int8
        echo ASR_DEVICE=cpu
        echo FORCE_LANG=th
        echo ASR_ENABLE_MULTI=1
        echo ENABLE_DIARIZATION=0
        echo KENLM_ARPA_PATH=
        echo RANK_ALPHA_ASR=1.0
        echo RANK_BETA_LM=1.2
        echo RANK_GAMMA_LEX=0.3
        echo RANK_DELTA_PEN=0.2
        echo DOMAIN_WHITELIST=
    ) > .env
    echo [INFO] สร้าง .env เรียบร้อย
)

echo.
echo [INFO] กำลังรัน Uvicorn...
echo URL: http://127.0.0.1:8000
echo Docs: http://127.0.0.1:8000/docs
echo.

python -m uvicorn app:app --host 0.0.0.0 --port 8000 --reload --log-level info


echo.
echo [INFO] Uvicorn หยุดทำงานแล้ว
pause
