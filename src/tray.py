from __future__ import annotations

import threading
from collections.abc import Callable

import pystray
from PIL import Image, ImageDraw

from src.state import AppState


def _icon_image(connected: bool) -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if connected:
        draw.ellipse((8, 8, 56, 56), fill=(216, 196, 160, 255))
    else:
        draw.ellipse((8, 8, 56, 56), outline=(216, 196, 160, 255), width=6)
    return img


class Tray:
    def __init__(
        self,
        *,
        on_show: Callable[[], None],
        on_connect: Callable[[], None],
        on_disconnect: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self.on_show = on_show
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.on_quit = on_quit
        self._state = AppState.DISCONNECTED
        self._icon = pystray.Icon(
            "fq-gate",
            _icon_image(False),
            "fq-gate",
            menu=pystray.Menu(
                pystray.MenuItem("打开窗口", lambda *_: self.on_show(), default=True),
                pystray.MenuItem(
                    "连接",
                    lambda *_: self.on_connect(),
                    enabled=lambda _item: self._state not in (AppState.CONNECTING, AppState.CONNECTED),
                    visible=lambda _item: self._state != AppState.CONNECTED,
                ),
                pystray.MenuItem(
                    "断开",
                    lambda *_: self.on_disconnect(),
                    visible=lambda _item: self._state
                    in (AppState.CONNECTING, AppState.CONNECTED),
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", lambda *_: self.on_quit()),
            ),
        )

    def set_state(self, state: AppState) -> None:
        self._state = state
        self._icon.icon = _icon_image(state == AppState.CONNECTED)
        try:
            self._icon.update_menu()
        except Exception:
            pass

    def start(self) -> None:
        threading.Thread(target=self._icon.run, daemon=True).start()

    def stop(self) -> None:
        try:
            self._icon.stop()
        except Exception:
            pass
