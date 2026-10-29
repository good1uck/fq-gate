from enum import Enum


class AppState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


LABELS = {
    AppState.DISCONNECTED: "未连接",
    AppState.CONNECTING: "连接中",
    AppState.CONNECTED: "已连接",
    AppState.FAILED: "未连接",
}
