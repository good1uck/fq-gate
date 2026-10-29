"""Bundled Mihomo only. Friends do not need Clash Verge."""

from __future__ import annotations

from pathlib import Path

from src.paths import vendor_dir


class KernelError(RuntimeError):
    pass


def find_mihomo() -> Path:
    for name in ("mihomo.exe", "verge-mihomo.exe"):
        path = vendor_dir() / name
        if path.is_file():
            return path
    raise KernelError("未找到自带 Mihomo 内核")
