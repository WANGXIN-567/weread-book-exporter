@echo off
chcp 65001 >nul
set PYTHONUTF8=1

if exist "F:\AI\workbuddy\2026-10-30-20-57-36\weread-md\.venv\Scripts\python.exe" (
    set "PY_EXE=F:\AI\workbuddy\2026-10-30-20-57-36\weread-md\.venv\Scripts\python.exe"
) else if exist "%~dp0.venv\Scripts\python.exe" (
    set "PY_EXE=%~dp0.venv\Scripts\python.exe"
) else (
    set "PY_EXE=python"
)

if "%~1"=="" (
    echo.
    echo ============================================================
    echo   📚 微信读书一键导出工具 (WeRead Book Exporter)
    echo ============================================================
    echo.
    set /p "BOOK_INPUT=请输入微信读书网页链接或书籍 ID: "
    if not "%BOOK_INPUT%"=="" (
        "%PY_EXE%" "%~dp0main.py" "%BOOK_INPUT%"
    )
) else (
    "%PY_EXE%" "%~dp0main.py" %*
)

pause
