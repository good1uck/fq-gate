"""Machine-readable UI state. Testers read this instead of screenshots."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from src.paths import log_dir
from src.state import AppState, LABELS

STATUS_PATH = log_dir() / "status.json"


def write_status(state: AppState, detail: str = "") -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "state": state.value,
        "label": LABELS[state],
        "detail": detail,
        "ts": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
