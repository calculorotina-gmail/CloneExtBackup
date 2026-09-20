<#
.SYNOPSIS
    Installs and registers the Chrome Extension Backup Pro Native Messaging Host in Windows.
.PARAMETER ExtensionId
    Optional Chrome Extension ID to authorize. Defaults to the pinned deterministic extension ID.
#>
param(
    [string]$ExtensionId = "mdimfmpnjkfmebafopcfildiicfegmjk"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ManifestPath = Join-Path $ScriptDir "com.extbackup.pro.json"
$BatPath = Join-Path $ScriptDir "ext_backup_host.bat"

Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "   Instalador PowerShell - Chrome Extension Backup Pro Host" -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] A verificar componentes em: $ScriptDir" -ForegroundColor Yellow
if (-not (Test-Path $BatPath)) {
    Write-Error "Launcher ext_backup_host.bat não encontrado em $BatPath"
}

Write-Host "[2/3] A configurar manifesto $ManifestPath com Extension ID: $ExtensionId" -ForegroundColor Yellow
$manifest = Get-Content -Raw -Path $ManifestPath | ConvertFrom-Json
$manifest.path = $BatPath
$origin = "chrome-extension://$ExtensionId/"
if ($manifest.allowed_origins -notcontains $origin) {
    $manifest.allowed_origins += $origin
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Path $ManifestPath -Encoding UTF8

Write-Host "[3/4] A registar no Registo do Windows (Chrome e Edge)..." -ForegroundColor Yellow
$regPathChrome = "HKCU:\Software\Google\Chrome\NativeMessagingHosts\com.extbackup.pro"
if (-not (Test-Path $regPathChrome)) {
    New-Item -Path $regPathChrome -Force | Out-Null
}
Set-ItemProperty -Path $regPathChrome -Name "(Default)" -Value $ManifestPath

$regPathEdge = "HKCU:\Software\Microsoft\Edge\NativeMessagingHosts\com.extbackup.pro"
if (-not (Test-Path $regPathEdge)) {
    New-Item -Path $regPathEdge -Force | Out-Null
}
Set-ItemProperty -Path $regPathEdge -Name "(Default)" -Value $ManifestPath

Write-Host "[4/4] A registar associação de ficheiros .crxbackup no Windows..." -ForegroundColor Yellow
$regExt = "HKCU:\Software\Classes\.crxbackup"
if (-not (Test-Path $regExt)) { New-Item -Path $regExt -Force | Out-Null }
Set-ItemProperty -Path $regExt -Name "(Default)" -Value "ChromeExtensionBackup.Archive"

$regProg = "HKCU:\Software\Classes\ChromeExtensionBackup.Archive"
if (-not (Test-Path $regProg)) { New-Item -Path $regProg -Force | Out-Null }
Set-ItemProperty -Path $regProg -Name "(Default)" -Value "Chrome Extension Backup Archive"

$regCmd = "HKCU:\Software\Classes\ChromeExtensionBackup.Archive\shell\open\command"
if (-not (Test-Path $regCmd)) { New-Item -Path $regCmd -Force | Out-Null }
Set-ItemProperty -Path $regCmd -Name "(Default)" -Value "cmd.exe /c start chrome.exe chrome-extension://$ExtensionId/ui/index.html"

Write-Host ""
Write-Host "[SUCESSO] Native Messaging Host e extensão .crxbackup registados com sucesso!" -ForegroundColor Green
Write-Host "Registo Chrome:      $regPathChrome" -ForegroundColor Gray
Write-Host "Registo Edge:        $regPathEdge" -ForegroundColor Gray
Write-Host "Associação Ficheiro: .crxbackup -> Chrome Extension Backup Pro" -ForegroundColor Gray
Write-Host "Manifesto:           $ManifestPath" -ForegroundColor Gray
Write-Host ""
