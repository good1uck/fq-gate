"""Headless full-pool screen. No TUN, no GUI."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

import yaml
from loguru import logger

from src.paths import log_dir, nodes_file
from src.pool import refresh_pool
from src.sieve import is_udp_proxy

LOG_DIR = log_dir()
RESULT_PATH = LOG_DIR / "sieve.json"


def _now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger.remove()
    logger.add(LOG_DIR / "sieve.log", rotation="1 MB", encoding="utf-8")
    started = time.monotonic()
    payload: dict = {
        "done": False,
        "ok": False,
        "alive": 0,
        "udp": 0,
        "other": 0,
        "error": None,
        "ts": _now(),
        "elapsed_s": 0,
    }
    try:
        count = refresh_pool(screen=True)
        data = yaml.safe_load(nodes_file().read_text(encoding="utf-8")) or {}
        proxies = data.get("proxies") or []
        udp = sum(1 for p in proxies if isinstance(p, dict) and is_udp_proxy(p))
        payload["alive"] = count
        payload["udp"] = udp
        payload["other"] = max(0, count - udp)
        payload["ok"] = count > 0
        if count == 0:
            payload["error"] = "筛选后 0 个节点"
    except Exception as exc:
        payload["error"] = str(exc)
    payload["elapsed_s"] = round(time.monotonic() - started, 1)
    payload["done"] = True
    payload["ts"] = _now()
    RESULT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
