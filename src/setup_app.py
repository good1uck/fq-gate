"""One-file installer. Unpacks payload.zip into %LOCALAPPDATA%\\fq-gate."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
import winreg
import zipfile
from ctypes import wintypes
from pathlib import Path

from src.paths import VERSION


def _payload() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
        path = base / "payload.zip"
        if path.is_file():
            return path
    root = Path(__file__).resolve().parent.parent
    for candidate in (root / "build" / "payload.zip", root / "dist" / "payload.zip"):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("找不到安装包 payload.zip")


def _dest() -> Path:
    return Path(os.environ["LOCALAPPDATA"]) / "fq-gate"


def _desktop() -> Path:
    buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
    ctypes.windll.shell32.SHGetFolderPathW(None, 0x0010, None, 0, buf)
    return Path(buf.value)


def _kill() -> None:
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    subprocess.run(
        ["taskkill", "/F", "/IM", "fq-gate.exe"],
        capture_output=True,
        creationflags=flags,
    )
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process | Where-Object { $_.Name -match 'mihomo' -and $_.CommandLine -match 'fq-gate-' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }",
        ],
        capture_output=True,
        creationflags=flags,
    )


def _shortcut(path: Path, target: Path, workdir: Path) -> None:
    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    script = (
        f"$w = New-Object -ComObject WScript.Shell; "
        f"$s = $w.CreateShortcut('{str(path).replace(chr(39), chr(39)+chr(39))}'); "
        f"$s.TargetPath = '{str(target).replace(chr(39), chr(39)+chr(39))}'; "
        f"$s.WorkingDirectory = '{str(workdir).replace(chr(39), chr(39)+chr(39))}'; "
        f"$s.Description = 'fq-gate'; "
        f"$s.Save()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        check=True,
        capture_output=True,
        creationflags=flags,
    )


def _register(dest: Path, exe: Path) -> None:
    uninstall = dest / "uninstall.ps1"
    key = winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Uninstall\fq-gate",
    )
    try:
        winreg.SetValueEx(key, "DisplayName", 0, winreg.REG_SZ, "fq-gate")
        winreg.SetValueEx(key, "DisplayVersion", 0, winreg.REG_SZ, VERSION)
        winreg.SetValueEx(key, "Publisher", 0, winreg.REG_SZ, "fq-gate")
        winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, str(dest))
        winreg.SetValueEx(key, "DisplayIcon", 0, winreg.REG_SZ, str(exe))
        winreg.SetValueEx(
            key,
            "UninstallString",
            0,
            winreg.REG_SZ,
            f'powershell.exe -NoProfile -ExecutionPolicy Bypass -File "{uninstall}"',
        )
        winreg.SetValueEx(key, "NoModify", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "NoRepair", 0, winreg.REG_DWORD, 1)
    finally:
        winreg.CloseKey(key)


def install() -> Path:
    dest = _dest()
    dest.mkdir(parents=True, exist_ok=True)
    _kill()
    with zipfile.ZipFile(_payload()) as zf:
        zf.extractall(dest)
    exe = dest / "fq-gate.exe"
    if not exe.is_file():
        raise FileNotFoundError(f"安装后找不到 {exe}")
    _shortcut(_desktop() / "fq-gate.lnk", exe, dest)
    programs = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs"
    programs.mkdir(parents=True, exist_ok=True)
    _shortcut(programs / "fq-gate.lnk", exe, dest)
    _register(dest, exe)
    return dest


def main() -> int:
    if "--silent" in sys.argv:
        try:
            dest = install()
            log_dir = dest / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            (log_dir / "setup.log").write_text(f"ok {VERSION}\n", encoding="utf-8")
            return 0
        except Exception as exc:
            Path(os.environ.get("TEMP", ".")).joinpath("fq-gate-setup.log").write_text(
                str(exc), encoding="utf-8"
            )
            return 1

    import tkinter as tk
    from tkinter import messagebox

    root = tk.Tk()
    root.title("fq-gate")
    root.geometry("360x140")
    root.resizable(False, False)
    label = tk.Label(root, text="正在安装 fq-gate…", font=("Segoe UI", 12))
    label.pack(expand=True)
    root.update()
    try:
        install()
        messagebox.showinfo("fq-gate", "装好了。桌面上有 fq-gate，打开后点大按钮。")
        return 0
    except Exception as exc:
        messagebox.showerror("fq-gate", f"安装失败：{exc}")
        return 1
    finally:
        try:
            root.destroy()
        except tk.TclError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
