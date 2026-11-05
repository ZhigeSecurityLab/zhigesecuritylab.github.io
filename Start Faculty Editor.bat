@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>nul
  if errorlevel 1 (
    python -m venv .venv
  ) else (
    py -3 -m venv .venv
  )
)
if not exist ".venv\Scripts\python.exe" (
  echo Python 3.9 or newer is required.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -c "import markdown_it" >nul 2>nul
if errorlevel 1 (
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    pause
    exit /b 1
  )
)
".venv\Scripts\python.exe" scripts\faculty.py --open
if errorlevel 1 pause
