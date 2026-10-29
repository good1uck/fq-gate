# Stop tunnel, remove install, restore desktop shortcuts.
$ErrorActionPreference = "Continue"
$dest = Join-Path $env:LOCALAPPDATA "fq-gate"

Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match 'mihomo' -and $_.CommandLine -match 'fq-gate-'
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Get-CimInstance Win32_Process | Where-Object {
    $_.CommandLine -match 'src\.main' -or $_.Name -eq 'fq-gate.exe'
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Start-Sleep -Seconds 1

$desktop = [Environment]::GetFolderPath("Desktop")
Remove-Item (Join-Path $desktop "fq-gate.lnk") -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs\fq-gate.lnk") -Force -ErrorAction SilentlyContinue

if (Test-Path $dest) {
    Remove-Item $dest -Recurse -Force -ErrorAction SilentlyContinue
}

Remove-Item "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\fq-gate" -Recurse -ErrorAction SilentlyContinue

Write-Host "fq-gate removed."
