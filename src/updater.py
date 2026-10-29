"""Background node refresh. App binary update waits for a filled manifest_url."""

from __future__ import annotations

import json
import threading
import time
from collections.abc import Callable
from pathlib import Path

from loguru import logger

from src.paths import VERSION, app_root
from src.pool import refresh_pool

_INTERVAL_SEC = 30 * 60


def _channel_path() -> Path:
    return app_root() / "config" / "channel.json"


def load_channel() -> dict:
    path = _channel_path()
    if not path.is_file():
        return {"version": VERSION, "manifest_url": ""}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": VERSION, "manifest_url": ""}
    if not isinstance(data, dict):
        return {"version": VERSION, "manifest_url": ""}
    return data


def refresh_once() -> None:
    try:
        count = refresh_pool()
        logger.info(f"后台刷新节点 {count}")
    except Exception as exc:
        logger.warning(f"后台刷新失败: {exc}")


def start_background(is_busy: Callable[[], bool] | None = None) -> None:
    def _loop() -> None:
        time.sleep(2)
        if is_busy and is_busy():
            logger.info("已连接，跳过本轮节点刷新")
        else:
            refresh_once()
        while True:
            time.sleep(_INTERVAL_SEC)
            if is_busy and is_busy():
                logger.info("已连接，跳过本轮节点刷新")
                continue
            refresh_once()

    threading.Thread(target=_loop, daemon=True, name="fq-gate-updater").start()
    logger.info("节点后台更新已启动")
