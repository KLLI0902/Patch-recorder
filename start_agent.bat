@echo off
setlocal
cd /d "%~dp0"

REM Avoid duplicate instances if task triggers twice
powershell -NoProfile -Command ^
  "$p = Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like '*firmware-agent*main.py*' }; if ($p) { exit 1 } else { exit 0 }"
if %errorlevel% equ 1 (
    echo [%date% %time%] Agent already running, skip.>> logs\startup.log
    exit /b 0
)

if not exist logs mkdir logs
echo [%date% %time%] Starting Firmware Agent...>> logs\startup.log

REM Prefer the Python used by this project; fall back to PATH
set "PYTHON_EXE=%LOCALAPPDATA%\Python\bin\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

"%PYTHON_EXE%" main.py >> logs\startup.log 2>&1
