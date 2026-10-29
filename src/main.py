"""One-button full-tunnel client."""

from __future__ import annotations

import sys
import threading
from loguru import logger

from src.connector import Connector, ConnectorError
from src.elevate import is_admin, relaunch_elevated
from src.paths import VERSION, app_root, log_dir
from src.state import AppState
from src.status_file import write_status
from src.tray import Tray
from src.ui import GateWindow
from src.updater import start_background

ROOT = app_root()
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LOG_DIR = log_dir()
logger.remove()
if sys.stderr is not None:
    logger.add(sys.stderr, level="INFO")
logger.add(LOG_DIR / "gate.log", rotation="1 MB", encoding="utf-8")


class App:
    def __init__(self) -> None:
        self.connector = Connector()
        self.state = AppState.DISCONNECTED
        self.window = GateWindow(on_toggle=self.toggle, on_quit=self.quit)
        self.tray = Tray(
            on_show=self._ui(self.window.show),
            on_connect=self._ui(self.connect),
            on_disconnect=self._ui(self.disconnect),
            on_quit=self._ui(self.quit),
        )

    def _ui(self, fn):
        def _wrap(*_args):
            self.window.root.after(0, fn)

        return _wrap

    def _set(self, state: AppState) -> None:
        self.state = state
        self.window.set_state(state)
        self.tray.set_state(state)
        write_status(state)

    def toggle(self) -> None:
        if self.state in (AppState.CONNECTING, AppState.CONNECTED):
            self.disconnect()
            return
        self.connect()

    def connect(self) -> None:
        if self.state in (AppState.CONNECTING, AppState.CONNECTED):
            return
        if sys.platform == "win32" and not is_admin():
            logger.info("TUN 需要管理员，弹出 UAC")
            if relaunch_elevated(["--connect"]):
                self.quit()
                return
            logger.error("用户拒绝了管理员权限")
            self._set(AppState.FAILED)
            return
        self._set(AppState.CONNECTING)
        threading.Thread(target=self._connect_worker, daemon=True).start()

    def _connect_worker(self) -> None:
        try:
            self.connector.connect()
        except ConnectorError as exc:
            logger.error(f"连接失败: {exc}")
            target = AppState.DISCONNECTED if str(exc) == "已取消" else AppState.FAILED
            self.window.root.after(0, lambda s=target: self._apply_if_connecting(s))
            return
        self.window.root.after(0, lambda: self._apply_if_connecting(AppState.CONNECTED))

    def _apply_if_connecting(self, state: AppState) -> None:
        if self.state == AppState.CONNECTING:
            self._set(state)

    def disconnect(self) -> None:
        try:
            self.connector.disconnect()
        except Exception as exc:
            logger.error(f"断开失败: {exc}")
        self._set(AppState.DISCONNECTED)

    def quit(self) -> None:
        # pystray 的退出必须在菜单回调里尽快返回，stop() 不能在同一线程里硬等。
        def _shutdown() -> None:
            try:
                self.connector.disconnect()
            except Exception:
                pass
            try:
                self.window.root.after(0, self.window.root.destroy)
            except Exception:
                pass
            try:
                self.tray.stop()
            except Exception:
                pass

        threading.Thread(target=_shutdown, daemon=True).start()

    def run(self) -> None:
        start_background(lambda: self.connector.running)
        self.tray.start()
        logger.info(f"fq-gate {VERSION} started")
        self.window.loop()
        try:
            self.connector.disconnect()
        except Exception:
            pass


if __name__ == "__main__":
    app = App()
    if "--connect" in sys.argv:
        app.window.root.after(500, app.connect)
    app.run()
