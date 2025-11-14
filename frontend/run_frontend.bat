@echo off
title ASR Local Dialect - Frontend
echo 🎨 เริ่มต้น ASR Local Dialect Frontend...
echo.

REM ตรวจ package.json
if not exist package.json (
    echo ❌ ไม่พบไฟล์ package.json กรุณารันสคริปต์นี้ในโฟลเดอร์ frontend
    pause
    exit /b
)

REM ตรวจ Node.js
where node >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ Node.js กรุณาติดตั้ง Node.js 18+
    pause
    exit /b
)

REM ตรวจ npm
where npm >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ ไม่พบ npm กรุณาติดตั้ง npm
    pause
    exit /b
)

REM ติดตั้ง node_modules ถ้าไม่มี
if not exist node_modules (
    echo 📦 ติดตั้ง dependencies...
    npm install
) else (
    echo ✅ Dependencies ติดตั้งแล้ว
)

REM สร้าง .env.local ถ้ายังไม่มี
if not exist .env.local (
    echo ⚙️  สร้างไฟล์ .env.local...
    echo NEXT_PUBLIC_API_URL=http://127.0.0.1:8000 > .env.local
    echo ✅ สร้างไฟล์ .env.local เรียบร้อย
)

echo.
echo ✨ เริ่มรัน Frontend บนพอร์ต 3000...
echo 📍 เปิดเว็บได้ที่: http://localhost:3000
echo ⚠️  หมายเหตุ: Backend ต้องรันอยู่ก่อนที่ http://127.0.0.1:8000
echo กด Ctrl+C เพื่อหยุด
echo.

npm run dev
pause
