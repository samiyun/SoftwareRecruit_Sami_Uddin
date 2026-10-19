@echo off
setlocal enabledelayedexpansion

rem ---------------------------------------------------------------------------
rem  TMR UI - one-click launcher
rem  Starts the FastAPI backend in its own window, opens the web app, then runs
rem  the image sender in this window. Press Ctrl+C to stop the sender.
rem ---------------------------------------------------------------------------

rem Always work from this script's own folder (UI/)
cd /d "%~dp0"

set "BACKEND=%~dp0backend"
set "SAMPLES=%BACKEND%\data\samples"
set "URL=http://127.0.0.1:8000/app/"

rem --- locate a Python interpreter ------------------------------------------
set "PY=python"
python --version >nul 2>nul
if errorlevel 1 (
    py --version >nul 2>nul
    if errorlevel 1 (
        echo [ERROR] Python was not found. Install Python 3.10+ and add it to PATH.
        pause
        exit /b 1
    )
    set "PY=py"
)

rem --- optional self-check:  run.bat --check --------------------------------
if /I "%~1"=="--check" (
    echo Backend folder : "%BACKEND%"
    echo Samples folder : "%SAMPLES%"
    echo App URL        : %URL%
    echo Python         : %PY%
    %PY% -c "import fastapi, uvicorn, websockets" >nul 2>nul
    if errorlevel 1 (echo Dependencies   : MISSING) else (echo Dependencies   : OK)
    exit /b 0
)

echo ==========================================
echo   TMR UI  -  backend + image sender
echo ==========================================
echo.

rem --- install dependencies if needed ---------------------------------------
%PY% -c "import fastapi, uvicorn, websockets" >nul 2>nul
if errorlevel 1 (
    echo Installing Python dependencies...
    %PY% -m pip install -r "%BACKEND%\requirements.txt"
    if errorlevel 1 (
        echo [ERROR] Could not install dependencies.
        pause
        exit /b 1
    )
)

rem --- start backend in its own window --------------------------------------
echo Starting backend on http://127.0.0.1:8000 ...
start "TMR backend" /D "%BACKEND%" cmd /k "%PY% -m uvicorn main:app --port 8000"

rem --- wait a moment, then open the app in the default browser --------------
timeout /t 3 /nobreak >nul
start "" "%URL%"

rem --- run the sender in this window (Ctrl+C to stop) -----------------------
echo.
echo Sending images from "%SAMPLES%"  -  press Ctrl+C to stop.
echo Use your own folder with:  %PY% "%BACKEND%\sender.py" --folder "C:\path\to\images"
echo.
%PY% "%BACKEND%\sender.py" --folder "%SAMPLES%"

echo.
echo Sender stopped.
pause
