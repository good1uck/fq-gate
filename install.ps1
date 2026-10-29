# Install fq-gate for the current user. Run from the folder that contains start.bat or fq-gate.exe.
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$dest = Join-Path $env:LOCALAPPDATA "fq-gate"

Write-Host "Installing to $dest"
New-Item -ItemType Directory -Force -Path $dest | Out-Null

$skip = @(".venv", "logs", "__pycache__", ".git", "dist", "build")
Get-ChildItem $here -Force | ForEach-Object {
    if ($skip -contains $_.Name) { return }
    $target = Join-Path $dest $_.Name
    if ($_.PSIsContainer) {
        Copy-Item $_.FullName $target -Recurse -Force
    } else {
        Copy-Item $_.FullName $target -Force
    }
}

$launch = Join-Path $dest "fq-gate.exe"
if (-not (Test-Path $launch)) {
    $launch = Join-Path $dest "start.bat"
}

$desktop = [Environment]::GetFolderPath("Desktop")
$w = New-Object -ComObject WScript.Shell
$lnk = $w.CreateShortcut((Join-Path $desktop "fq-gate.lnk"))
$lnk.TargetPath = $launch
$lnk.WorkingDirectory = $dest
$lnk.Description = "fq-gate"
$lnk.Save()

$programs = Join-Path $env:APPDATA "Microsoft\Windows\Start Menu\Programs"
New-Item -ItemType Directory -Force -Path $programs | Out-Null
$lnk2 = $w.CreateShortcut((Join-Path $programs "fq-gate.lnk"))
$lnk2.TargetPath = $launch
$lnk2.WorkingDirectory = $dest
$lnk2.Save()

Write-Host "Done. Shortcut: Desktop and Start Menu -> fq-gate"
Write-Host "Uninstall: $dest\uninstall.ps1"
