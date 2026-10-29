"""Start/stop a dedicated Mihomo with TUN. Independent of Clash Verge's instance."""

from __future__ import annotations

import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import httpx
import yaml
from loguru import logger

from src.config_builder import PROBE_URL, build_config
from src.kernel import KernelError, find_mihomo
from src.paths import nodes_file, vendor_dir
from src.pool import refresh_pool


class ConnectorError(RuntimeError):
    pass


def _read_proxies(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    collected: list[dict] = []
    seen: set[str] = set()
    for item in data.get("proxies") or []:
        if not isinstance(item, dict) or not item.get("name"):
            continue
        key = f"{item.get('type')}|{item.get('server')}|{item.get('port')}"
        if key in seen:
            continue
        seen.add(key)
        collected.append(item)
    return collected


def load_proxies() -> list[dict]:
    collected = _read_proxies(nodes_file())
    if collected:
        return collected
    try:
        refresh_pool(screen=False)
    except Exception as exc:
        logger.warning(f"节点池刷新失败: {exc}")
    collected = _read_proxies(nodes_file())
    if collected:
        return collected
    raise ConnectorError("没有可用节点")


def _kill_orphan_mihomo() -> None:
    """清掉上次异常退出留下的 fq-gate 内核，避免占着同名 TUN 网卡。"""
    cmd = (
        "Get-CimInstance Win32_Process "
        "| Where-Object { $_.Name -match 'mihomo' -and $_.CommandLine -match 'fq-gate-' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
    )
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            timeout=15,
            check=False,
            capture_output=True,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.warning(f"清理残留内核失败: {exc}")


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class Connector:
    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._work_dir: Path | None = None
        self._controller_port: int | None = None
        self._secret: str = ""
        self._lock = threading.Lock()
        self._cancel = threading.Event()

    @property
    def running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def connect(self, timeout: float = 35.0) -> None:
        self._cancel.clear()
        _kill_orphan_mihomo()
        if not nodes_file().is_file():
            try:
                refresh_pool(screen=False)
            except Exception as exc:
                logger.warning(f"连接前刷新节点失败: {exc}")
        with self._lock:
            if self.running:
                return
            self._spawn_locked()
        try:
            self._wait_ready(timeout=8.0)
            self._raise_if_tun_failed()
            self._wait_global_alive(timeout=min(12.0, timeout))
            self._raise_if_tun_failed()
            self._wait_probe(timeout=timeout)
        except Exception:
            self.disconnect()
            raise

    def _spawn_locked(self) -> None:
        proxies = load_proxies()
        try:
            engine = find_mihomo()
        except KernelError as exc:
            raise ConnectorError(str(exc)) from exc
        work_dir = Path(tempfile.mkdtemp(prefix="fq-gate-"))
        controller_port = _free_port()
        mixed_port = _free_port()
        secret = f"gate-{controller_port}"
        config = build_config(
            proxies,
            controller_port=controller_port,
            mixed_port=mixed_port,
            secret=secret,
        )
        config_path = work_dir / "config.yaml"
        config_path.write_text(
            yaml.dump(config, allow_unicode=True, sort_keys=False, width=200),
            encoding="utf-8",
        )
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        wintun = vendor_dir() / "wintun.dll"
        if wintun.is_file():
            shutil.copy2(wintun, work_dir / "wintun.dll")
        log_path = work_dir / "mihomo.log"
        log_f = log_path.open("wb")
        logger.info(f"启动 Mihomo TUN engine={engine} work={work_dir}")
        try:
            proc = subprocess.Popen(
                [str(engine), "-f", str(config_path), "-d", str(work_dir)],
                cwd=str(work_dir),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                **kwargs,
            )
        except OSError as exc:
            log_f.close()
            raise ConnectorError(f"无法启动内核: {exc}") from exc
        self._proc = proc
        self._work_dir = work_dir
        self._controller_port = controller_port
        self._secret = secret

    def disconnect(self) -> None:
        self._cancel.set()
        with self._lock:
            proc = self._proc
            work_dir = self._work_dir
            self._proc = None
            self._work_dir = None
            self._controller_port = None
            self._secret = ""
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)
        if work_dir is not None:
            try:
                shutil.rmtree(work_dir, ignore_errors=True)
            except OSError:
                pass
        logger.info("隧道已关闭")

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._secret}"}

    def _wait_ready(self, timeout: float) -> None:
        url = f"http://127.0.0.1:{self._controller_port}/version"
        deadline = time.monotonic() + timeout
        with httpx.Client(trust_env=False, timeout=0.6) as client:
            while time.monotonic() < deadline:
                self._raise_if_cancelled()
                self._raise_if_tun_failed()
                if self._proc is not None and self._proc.poll() is not None:
                    raise ConnectorError(self._crash_reason())
                try:
                    resp = client.get(url, headers=self._headers())
                    if resp.status_code == 200:
                        logger.info(f"Mihomo API 就绪 {resp.text.strip()}")
                        return
                except (httpx.HTTPError, OSError):
                    pass
                time.sleep(0.15)
        raise ConnectorError("内核没有就绪")

    def _wait_global_alive(self, timeout: float) -> None:
        # 不要打 /group/GLOBAL/delay：TUN 失败时它会卡住整组测试。
        url = f"http://127.0.0.1:{self._controller_port}/proxies/GLOBAL"
        deadline = time.monotonic() + timeout
        with httpx.Client(trust_env=False, timeout=2.0) as client:
            while time.monotonic() < deadline:
                self._raise_if_cancelled()
                self._raise_if_tun_failed()
                if self._proc is not None and self._proc.poll() is not None:
                    raise ConnectorError(self._crash_reason())
                try:
                    resp = client.get(url, headers=self._headers())
                    data = resp.json() if resp.status_code == 200 else {}
                    now = data.get("now") if isinstance(data, dict) else None
                    if now:
                        logger.info(f"GLOBAL 已选 {now}")
                        return
                except (httpx.HTTPError, OSError, ValueError):
                    pass
                time.sleep(0.3)
        raise ConnectorError("节点握手失败")

    def _wait_probe(self, timeout: float) -> None:
        """TUN 起来之后，本机必须能打开 grok.com，才算已连接。"""
        deadline = time.monotonic() + timeout
        last_error = "Grok 探测失败"
        with httpx.Client(
            trust_env=False,
            follow_redirects=True,
            timeout=httpx.Timeout(8.0, connect=5.0),
            headers={"User-Agent": "Mozilla/5.0 fq-gate"},
        ) as client:
            while time.monotonic() < deadline:
                self._raise_if_cancelled()
                self._raise_if_tun_failed()
                if self._proc is not None and self._proc.poll() is not None:
                    raise ConnectorError(self._crash_reason())
                try:
                    resp = client.get(PROBE_URL)
                    if resp.status_code in (200, 204):
                        logger.info(f"Grok 探测成功 status={resp.status_code}")
                        return
                    last_error = f"Grok 探测 status={resp.status_code}"
                except (httpx.HTTPError, OSError) as exc:
                    last_error = f"Grok 探测失败: {exc}"
                time.sleep(1.0)
        raise ConnectorError(last_error)

    def _raise_if_cancelled(self) -> None:
        if self._cancel.is_set():
            raise ConnectorError("已取消")

    def _raise_if_tun_failed(self) -> None:
        text = self._mihomo_log()
        if "Access is denied" in text:
            raise ConnectorError("TUN 需要管理员权限")
        if "Start TUN listening error" in text:
            raise ConnectorError("TUN 启动失败")

    def _mihomo_log(self) -> str:
        if self._work_dir is None:
            return ""
        log_file = self._work_dir / "mihomo.log"
        try:
            return log_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _crash_reason(self) -> str:
        log_tail = self._mihomo_log()[-400:]
        return f"内核退出 code={self._proc.returncode if self._proc else '?'} {log_tail}"
