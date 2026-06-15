@echo off
echo ========================================
echo  NovelAgent
echo ========================================
echo.
echo [1/2] Starting Backend (FastAPI :8001)...
start "NovelAgent-Backend" cmd /k "cd /d D:\NovelAgent && D:\annaconda\python.exe -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload"
echo.
echo [2/2] Starting Frontend (Vite :3001)...
start "NovelAgent-Frontend" cmd /k "cd /d D:\NovelAgent\frontend && npm run dev"
echo.
echo Backend: http://localhost:8001/docs
echo Frontend: http://localhost:3001
echo.
pause
