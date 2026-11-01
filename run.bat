@echo off
setlocal
chcp 65001 >nul
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8
cd /d "%~dp0"

set "PY_EXE="
if exist "F:\AI\workbuddy\2026-10-30-20-57-36\weread-md\.venv\Scripts\python.exe" set "PY_EXE=F:\AI\workbuddy\2026-10-30-20-57-36\weread-md\.venv\Scripts\python.exe"
if not defined PY_EXE if exist "%~dp0.venv\Scripts\python.exe" set "PY_EXE=%~dp0.venv\Scripts\python.exe"
if not defined PY_EXE set "PY_EXE=python"

"%PY_EXE%" -V >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and add it to PATH.
    pause
    exit /b 1
)

"%PY_EXE%" "%~dp0main.py" %*

echo.
pause