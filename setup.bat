@echo off
setlocal
cd /d "%~dp0"
title Royal Shetkari POS - first-time setup

echo ============================================================
echo  Royal Shetkari POS - first-time setup
echo  Needs: Windows 10/11, Python 3.12 or newer, internet (once)
echo ============================================================
echo.

REM ---- 1. Find Python 3.12+ ------------------------------------
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY goto :nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>nul
if errorlevel 1 goto :nopython
for /f "delims=" %%v in ('%PY% -c "import sys; print(sys.version.split()[0])"') do echo Using Python %%v

REM ---- 2. Private Python environment for the POS ----------------
if not exist ".venv\Scripts\python.exe" (
    echo Creating the POS's own Python environment in .venv ...
    %PY% -m venv .venv
    if errorlevel 1 goto :fail
)

REM ---- 3. Install the POS's Python packages (needs internet) ----
echo Installing packages (first time takes a few minutes)...
".venv\Scripts\python.exe" -m pip install --upgrade pip --disable-pip-version-check -q
if errorlevel 1 goto :fail
".venv\Scripts\python.exe" -m pip install -r requirements.txt --disable-pip-version-check -q
if errorlevel 1 goto :fail

REM ---- 4. Settings, database, Royal Shetkari menu and sample data ----
".venv\Scripts\python.exe" scripts\windows\local_setup.py --first-run
if errorlevel 1 goto :fail

echo.
echo ============================================================
echo  Setup finished.
echo  Sample staff logins: DEMO_LOGINS.txt (keep it private)
echo  From now on, double-click start.bat to open the POS.
echo ============================================================
echo.
choice /C YN /M "Start the POS now"
if errorlevel 2 goto :end
call "%~dp0start.bat"
goto :end

:nopython
echo.
echo Python 3.12 or newer was not found.
echo  1. Download it from https://www.python.org/downloads/windows/
echo  2. In the installer, tick "Add python.exe to PATH", then Install.
echo  3. Run setup.bat again.
echo.
pause
exit /b 1

:fail
echo.
echo Setup stopped because of the error above. Nothing was deleted.
echo Check your internet connection and run setup.bat again.
echo See WINDOWS_SETUP.md, section "If something goes wrong".
echo.
pause
exit /b 1

:end
endlocal
