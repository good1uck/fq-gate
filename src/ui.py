from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable

from src.state import AppState, LABELS

BG = "#171b22"
TEXT = "#f3f5f8"
MUTED = "#8b93a7"
OFF = "#3a4150"
WAIT = "#c9a227"
ON = "#d8c4a0"
WINDOW_BG = "#0e1116"


class GateWindow:
    def __init__(
        self,
        on_toggle: Callable[[], None],
        on_quit: Callable[[], None],
    ) -> None:
        self.on_toggle = on_toggle
        self.on_quit = on_quit
        self.state = AppState.DISCONNECTED
        self._spin = 0

        self.root = tk.Tk()
        self.root.title("fq-gate")
        self.root.configure(bg=WINDOW_BG)
        self.root.geometry("360x520")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.hide)

        self.card = tk.Frame(self.root, bg=BG, highlightthickness=0)
        self.card.place(relx=0.5, rely=0.5, anchor="center", width=360, height=520)

        self.canvas = tk.Canvas(
            self.card, width=360, height=280, bg=BG, highlightthickness=0, bd=0
        )
        self.canvas.pack(pady=(72, 0))
        self.canvas.bind("<Button-1>", lambda _e: self.on_toggle())

        self.status = tk.Label(
            self.card, text=LABELS[self.state], fg=TEXT, bg=BG, font=("Microsoft YaHei UI", 16, "bold")
        )
        self.status.pack(pady=(8, 0))

        self.hint = tk.Label(
            self.card, text="", fg=MUTED, bg=BG, font=("Microsoft YaHei UI", 10), cursor="hand2"
        )
        self.hint.pack(pady=(10, 0))
        self.hint.bind("<Button-1>", self._on_hint_click)

        self._draw()

    def hide(self) -> None:
        self.root.withdraw()

    def show(self) -> None:
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def set_state(self, state: AppState) -> None:
        self.state = state
        self.status.config(text=LABELS[state])
        if state == AppState.CONNECTED:
            self.hint.config(text="国内网站也会变慢", fg=MUTED, cursor="arrow")
        elif state == AppState.FAILED:
            self.hint.config(text="连不上，点此重试", fg=ON, cursor="hand2")
        else:
            self.hint.config(text="", fg=MUTED, cursor="arrow")
        self._draw()
        if state == AppState.CONNECTING:
            self._tick_spin()

    def _on_hint_click(self, _event: tk.Event) -> None:
        if self.state == AppState.FAILED:
            self.on_toggle()

    def _tick_spin(self) -> None:
        if self.state != AppState.CONNECTING:
            return
        self._spin = (self._spin + 12) % 360
        self._draw()
        self.root.after(40, self._tick_spin)

    def _draw(self) -> None:
        self.canvas.delete("all")
        cx, cy, r = 180, 150, 84
        if self.state == AppState.CONNECTED:
            ring, fill = ON, ON
        elif self.state == AppState.CONNECTING:
            ring, fill = WAIT, None
        else:
            ring, fill = OFF, OFF
        self.canvas.create_oval(cx - r, cy - r, cx + r, cy + r, outline=ring, width=10)
        inner = 43
        if self.state == AppState.CONNECTING:
            self._arc(cx, cy, 36, self._spin, WAIT)
        elif fill:
            self.canvas.create_oval(
                cx - inner, cy - inner, cx + inner, cy + inner, fill=fill, outline=fill
            )

    def _arc(self, cx: int, cy: int, radius: int, start_deg: int, color: str) -> None:
        # approximate a 270-degree spinner with short line segments
        points: list[float] = []
        for i in range(0, 270, 8):
            rad = math.radians(start_deg + i)
            points.append(cx + radius * math.cos(rad))
            points.append(cy + radius * math.sin(rad))
        if len(points) >= 4:
            self.canvas.create_line(*points, fill=color, width=6, capstyle=tk.ROUND, smooth=True)

    def loop(self) -> None:
        self.root.mainloop()
