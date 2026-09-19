@echo off
setlocal EnableDelayedExpansion

echo ================================================================
echo    Instalador do Native Messaging Host - Chrome Extension Backup Pro
echo ================================================================
echo.

set "SCRIPT_DIR=%~dp0"
REM Remove trailing backslash
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "MANIFEST_PATH=%SCRIPT_DIR%\com.extbackup.pro.json"
set "BAT_PATH=%SCRIPT_DIR%\ext_backup_host.bat"

REM Escape backslashes for JSON
set "ESCAPED_BAT_PATH=%BAT_PATH:\=\\%"

echo [1/3] A verificar caminhos locais...
echo       Diretório: %SCRIPT_DIR%
echo       Manifesto:  %MANIFEST_PATH%
echo       Launcher:   %BAT_PATH%
echo.

REM Update com.extbackup.pro.json with the absolute path of ext_backup_host.bat
echo [2/3] A atualizar com.extbackup.pro.json com o caminho absoluto deste computador...
powershell -NoProfile -Command ^
    "$jsonPath = '%MANIFEST_PATH%';" ^
    "$batPath = '%ESCAPED_BAT_PATH%';" ^
    "$extId = if ('%1' -ne '') { '%1' } else { 'mdimfmpnjkfmebafopcfildiicfegmjk' };" ^
    "$content = Get-Content -Raw -Path $jsonPath | ConvertFrom-Json;" ^
    "$content.path = $batPath;" ^
    "if ($content.allowed_origins -notcontains ('chrome-extension://' + $extId + '/')) { $content.allowed_origins += ('chrome-extension://' + $extId + '/'); }" ^
    "$content | ConvertTo-Json -Depth 5 | Set-Content -Path $jsonPath -Encoding UTF8;"

if %ERRORLEVEL% NEQ 0 (
    echo [ERRO] Falha ao atualizar o manifesto JSON.
    pause
    exit /b 1
)

echo [3/3] A registar o Native Messaging Host no Registo do Windows (HKCU)...
set "REG_KEY=HKCU\Software\Google\Chrome\NativeMessagingHosts\com.extbackup.pro"
set "EDGE_REG_KEY=HKCU\Software\Microsoft\Edge\NativeMessagingHosts\com.extbackup.pro"

reg add "%REG_KEY%" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f >nul
reg add "%EDGE_REG_KEY%" /ve /t REG_SZ /d "%MANIFEST_PATH%" /f >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================
    echo [SUCESSO] O componente local Windows foi registado com sucesso!
    echo Chave Chrome: %REG_KEY%
    echo Aponta para:  %MANIFEST_PATH%
    echo ================================================================
    echo.
    echo Pode agora abrir o Google Chrome e utilizar a extensao Chrome Extension Backup Pro.
) else (
    echo.
    echo [ERRO] Nao foi possivel adicionar a chave ao Registo do Windows.
    pause
    exit /b 1
)

echo.
pause
