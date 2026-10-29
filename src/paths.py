from __future__ import annotations

import sys
from pathlib import Path

VERSION = "0.6.3"


def app_root() -> Path:
    """Folder that holds vendor/, data/, logs/. Writable after install."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def data_dir() -> Path:
    path = app_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def log_dir() -> Path:
    path = app_root() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def vendor_dir() -> Path:
    return app_root() / "vendor"


def nodes_file() -> Path:
    return data_dir() / "nodes.yaml"
