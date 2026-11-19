@echo off
title Sistema de Inventario - Ambulatorio
cd /d "%~dp0"

if exist "venv\Scripts\activate.bat" (
    call "venv\Scripts\activate.bat"
)

start "" "http://127.0.0.1:8000"
uvicorn main:app --host 127.0.0.1 --port 8000
pause