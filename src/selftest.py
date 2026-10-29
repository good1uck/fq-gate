"""Headless Layer 5 probe. Doubao runs this instead of GUI screenshots."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from datetime import datetime, timezone

from src.config_builder import PROBE_URL
from src.connector import Connector, ConnectorError
from src.elevate import is_admin, relaunch_elevated
from src.paths import log_dir

LOG_DIR = log_dir()
RESULT_PATH = LOG_DIR / "selftest.json"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _write(payload: dict) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _adapter_up() -> bool:
    cmd = (
        "Get-NetAdapter -Name fq-gate -ErrorAction SilentlyContinue "
        "| Select-Object -ExpandProperty Status"
    )
    try:
        out = subprocess.check_output(
            ["powershell", "-NoProfile", "-Command", cmd],
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=15,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return out.strip().lower() == "up"


def _run() -> dict:
    started = time.monotonic()
    result: dict = {
        "done": False,
        "ok": False,
        "admin": is_admin(),
        "probe": PROBE_URL,
        "adapter_up": False,
        "grok": None,
        "adapter_cleared": False,
        "error": None,
        "ts": _now(),
        "elapsed_s": 0,
    }
    connector = Connector()
    try:
        connector.connect()
        result["grok"] = "connected"
        result["adapter_up"] = _adapter_up()
        if not result["adapter_up"]:
            raise ConnectorError("Grok 通了但网卡 fq-gate 未 Up")
        connector.disconnect()
        time.sleep(1.0)
        result["adapter_cleared"] = not _adapter_up()
        result["ok"] = bool(result["adapter_up"] and result["adapter_cleared"])
        if not result["adapter_cleared"]:
            result["error"] = "断开后 fq-gate 网卡仍在"
    except ConnectorError as exc:
        result["error"] = str(exc)
        try:
            connector.disconnect()
        except Exception:
            pass
        result["adapter_cleared"] = not _adapter_up()
    result["elapsed_s"] = round(time.monotonic() - started, 1)
    result["done"] = True
    result["ts"] = _now()
    return result


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32" and not is_admin() and "--child" not in sys.argv:
        if RESULT_PATH.exists():
            RESULT_PATH.unlink()
        if not relaunch_elevated(["--child"], module="src.selftest"):
            _write(
                {
                    "done": True,
                    "ok": False,
                    "admin": False,
                    "error": "用户拒绝了管理员权限",
                    "ts": _now(),
                }
            )
            print(RESULT_PATH)
            return 2
        for _ in range(180):
            if RESULT_PATH.exists():
                try:
                    data = json.loads(RESULT_PATH.read_text(encoding="utf-8"))
                except (OSError, json.JSONDecodeError):
                    data = {}
                if data.get("done"):
                    print(json.dumps(data, ensure_ascii=False, indent=2))
                    return 0 if data.get("ok") else 1
            time.sleep(0.5)
        _write({"done": True, "ok": False, "error": "等待提权自测超时", "ts": _now()})
        return 3

    payload = _run()
    _write(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
