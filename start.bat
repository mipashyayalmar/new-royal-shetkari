@echo off
setlocal
cd /d "%~dp0"
title Royal Shetkari

if not exist ".venv\Scripts\python.exe" (
    echo The POS is not installed on this PC yet. Double-click setup.bat first.
    pause
    exit /b 1
)

echo Preparing Royal Shetkari (backup + database check)...
".venv\Scripts\python.exe" scripts\windows\local_setup.py
if errorlevel 1 goto :fail

".venv\Scripts\python.exe" scripts\windows\serve.py
if errorlevel 1 goto :fail
goto :end

:fail
echo.
echo The POS could not start because of the error above.
echo See WINDOWS_SETUP.md, section "If something goes wrong".
pause
exit /b 1

:end
endlocal
