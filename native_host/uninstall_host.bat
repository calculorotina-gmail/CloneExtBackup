@echo off
setlocal

echo ================================================================
echo    Desinstalador do Native Host - Chrome Extension Backup Pro
echo ================================================================
echo.

set "REG_KEY=HKCU\Software\Google\Chrome\NativeMessagingHosts\com.extbackup.pro"

echo A remover chave do Registo do Windows: %REG_KEY%
reg delete "%REG_KEY%" /f >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [SUCESSO] O registo do Native Messaging Host foi removido com sucesso.
) else (
    echo [INFO] A chave de registo ja nao existia ou ja tinha sido removida.
)

echo.
pause
