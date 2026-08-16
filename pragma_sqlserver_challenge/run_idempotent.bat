@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta run_demo.bat
    pause
    exit /b 1
)

".venv\Scripts\python.exe" main.py

echo.
echo Si los archivos ya estaban procesados, deben aparecer como [SKIP]
echo y NO deben duplicarse.
pause
