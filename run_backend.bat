@echo off
REM Run Django backend with uvicorn (recommended for Windows)
cd /d %~dp0backend
call ..\venv\Scripts\activate.bat
python -m uvicorn config.asgi:application --host 0.0.0.0 --port 8000

