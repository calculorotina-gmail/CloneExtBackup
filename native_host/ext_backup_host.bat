@echo off
setlocal

where python.exe >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    python -u "%~dp0ext_backup_host.py" %*
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" -u "%~dp0ext_backup_host.py" %*
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" -u "%~dp0ext_backup_host.py" %*
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -u "%~dp0ext_backup_host.py" %*
    exit /b %ERRORLEVEL%
)

if exist "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" (
    "%LOCALAPPDATA%\Programs\Python\Python314\python.exe" -u "%~dp0ext_backup_host.py" %*
    exit /b %ERRORLEVEL%
)

python -u "%~dp0ext_backup_host.py" %*
