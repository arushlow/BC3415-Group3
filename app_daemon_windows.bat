@echo off
setlocal

set SERVER_TYPE=uvicorn

if "%~1" neq "" (
    set SERVER_TYPE=%~1
)

echo Using %SERVER_TYPE% to start app...

:loop
if /i "%SERVER_TYPE%"=="uvicorn" (
    python run_with_uvicorn.py
) else if /i "%SERVER_TYPE%"=="waitress" (
    python run_with_waitress.py
) else (
    echo Unsupported server type: %SERVER_TYPE%
    echo Supported server types are: uvicorn, waitress
    exit /b 1
)

echo Application crashed or stopped. Restarting...
goto loop