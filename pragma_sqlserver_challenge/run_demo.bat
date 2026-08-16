@echo off
setlocal
cd /d "%~dp0"

echo ============================================================
echo PRAGMA - DATA ENGINEER CHALLENGE
echo Python + SQL Server
echo ============================================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creando entorno virtual...
    %PYTHON_CMD% -m venv .venv
    if errorlevel 1 goto :error
) else (
    echo [1/4] Entorno virtual ya existe.
)

echo [2/4] Instalando dependencias...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo [3/4] Ejecutando prueba unitaria...
".venv\Scripts\python.exe" -m unittest discover -s tests -v
if errorlevel 1 goto :error

echo [4/4] Ejecutando pipeline completo desde cero...
".venv\Scripts\python.exe" main.py --reset
if errorlevel 1 goto :error

echo.
echo DEMOSTRACION FINALIZADA.
echo Ahora abre SSMS y ejecuta sql\02_validation_queries.sql
pause
exit /b 0

:error
echo.
echo OCURRIO UN ERROR.
echo Revisa README.md y config.ini.
pause
exit /b 1
