"""Windows UAC relaunch. TUN 建网卡必须管理员；GUI 点连接时再提权。"""

from __future__ import annotations

import ctypes
import subprocess
import sys
from src.paths import app_root


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def relaunch_elevated(extra: list[str] | None = None, module: str = "src.main") -> bool:
    """弹出 UAC，用同一解释器在项目根目录再开一份。用户拒绝则返回 False。"""
    extra = extra or []
    if getattr(sys, "frozen", False):
        params = subprocess.list2cmdline(extra)
    else:
        params = subprocess.list2cmdline(["-m", module, *extra])
    rc = ctypes.windll.shell32.ShellExecuteW(
        None,
        "runas",
        sys.executable,
        params,
        str(app_root()),
        1,
    )
    return int(rc) > 32
