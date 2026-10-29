# Build a friend-installable folder at dist\fq-gate
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path "vendor\mihomo.exe")) {
    throw "vendor\mihomo.exe missing"
}

& .\.venv\Scripts\python.exe -m pip install -q pyinstaller
& .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onedir --windowed `
    --contents-directory . `
    --name fq-gate `
    --hidden-import pystray `
    --hidden-import pystray._win32 `
    --hidden-import PIL `
    --hidden-import src.main `
    --hidden-import src.connector `
    --hidden-import src.pool `
    --hidden-import src.updater `
    --hidden-import src.sieve `
    --hidden-import src.kernel `
    --hidden-import yaml `
    --hidden-import httpx `
    --hidden-import loguru `
    src\main.py

$dist = Join-Path $PSScriptRoot "dist\fq-gate"
Copy-Item "vendor" $dist -Recurse -Force
Copy-Item "config" $dist -Recurse -Force
New-Item -ItemType Directory -Force -Path (Join-Path $dist "data") | Out-Null
if (Test-Path "data\nodes.yaml") {
    Copy-Item "data\nodes.yaml" (Join-Path $dist "data\nodes.yaml") -Force
}
Copy-Item "install.ps1","uninstall.ps1","install.bat","uninstall.bat","README.md" $dist -Force

$payload = Join-Path $PSScriptRoot "build\payload.zip"
New-Item -ItemType Directory -Force -Path (Join-Path $PSScriptRoot "build") | Out-Null
if (Test-Path $payload) { Remove-Item $payload -Force }
& "C:\Program Files\7-Zip\7z.exe" a -tzip -mx=5 $payload "$dist\*" | Out-Host
if (-not (Test-Path $payload)) { throw "payload.zip missing" }

& .\.venv\Scripts\pyinstaller.exe --noconfirm --onefile --windowed `
    --name fq-gate-setup `
    --workpath (Join-Path $PSScriptRoot "build\setup") `
    --specpath (Join-Path $PSScriptRoot "build\setup") `
    --add-data "$payload;." `
    --hidden-import src.paths `
    src\setup_app.py

$setup = Join-Path $PSScriptRoot "dist\fq-gate-setup.exe"
if (-not (Test-Path $setup)) { throw "fq-gate-setup.exe missing" }
Write-Host "Packed: $dist"
Write-Host "Installer: $setup"
Write-Host "Give friends fq-gate-setup.exe"
