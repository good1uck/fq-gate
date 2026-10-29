"""TCP prefilter + protocol delay, adapted from fq-forever-agent tester.

Runs a headless Mihomo with no TUN. Writes nothing; caller owns the cache.
"""

from __future__ import annotations

import asyncio
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

import httpx
import yaml
from loguru import logger

from src.config_builder import PROBE_URL
from src.kernel import KernelError, find_mihomo

UDP_TYPES = frozenset({"hysteria", "hysteria2", "tuic", "wireguard"})
_TCP_TIMEOUT = 3.0
_TCP_MAX_MS = 300.0
_TCP_CONCURRENCY = 50
_PROTO_TIMEOUT = 5.0
_PROTO_MAX_MS = 3000.0
_PROTO_CONCURRENCY = 10


def is_udp_proxy(item: dict) -> bool:
    return str(item.get("type", "")).lower() in UDP_TYPES


def filter_alive(proxies: list[dict]) -> list[dict]:
    if not proxies:
        return []
    try:
        alive = asyncio.run(_filter_async(proxies))
    except KernelError as exc:
        logger.error(f"筛选无法执行: {exc}")
        return []
    except Exception as exc:
        logger.error(f"筛选失败: {exc}")
        return []
    udp_n = sum(1 for p in alive if is_udp_proxy(p))
    logger.info(
        f"筛选保留全部可用 {len(alive)} 个 (HY2/TUIC 等 {udp_n} / 其他 {len(alive) - udp_n})"
    )
    return alive


async def _filter_async(proxies: list[dict]) -> list[dict]:
    tcp_nodes = [p for p in proxies if not is_udp_proxy(p)]
    udp_nodes = [p for p in proxies if is_udp_proxy(p)]
    if udp_nodes:
        logger.info(
            f"HY2/TUIC 等 {len(udp_nodes)} 个不做 TCP 预检，直接协议握手"
        )
    tcp_alive = await _tcp_filter(tcp_nodes)
    candidates = tcp_alive + udp_nodes
    if not candidates:
        return []
    return await _protocol_filter(candidates)


async def _tcp_filter(proxies: list[dict]) -> list[dict]:
    if not proxies:
        return []
    logger.info(
        f"开始 TCP 预检: {len(proxies)} 个节点, 并发={_TCP_CONCURRENCY}, "
        f"超时={_TCP_TIMEOUT}s, 最大延迟={_TCP_MAX_MS}ms"
    )
    sem = asyncio.Semaphore(_TCP_CONCURRENCY)

    async def _one(item: dict) -> tuple[dict, float | None]:
        async with sem:
            return item, await _tcp_latency(item)

    tested = await asyncio.gather(*[_one(p) for p in proxies])
    alive: list[dict] = []
    unreachable = 0
    too_slow = 0
    for item, latency in tested:
        if latency is None:
            unreachable += 1
            continue
        if latency > _TCP_MAX_MS:
            too_slow += 1
            continue
        alive.append(item)
    logger.info(
        f"TCP 测试完成: {len(alive)} 可用 / {too_slow} 延迟过高(>{_TCP_MAX_MS}ms) / "
        f"{unreachable} 不可达 / {len(proxies)} 总计"
    )
    return alive


async def _tcp_latency(item: dict) -> float | None:
    server = item.get("server")
    port = item.get("port")
    if not server or not port:
        return None
    try:
        port_i = int(port)
    except (TypeError, ValueError):
        return None
    start = time.perf_counter()
    try:
        _reader, writer = await asyncio.wait_for(
            asyncio.open_connection(str(server), port_i),
            timeout=_TCP_TIMEOUT,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return round(elapsed_ms, 1)
    except (asyncio.TimeoutError, OSError):
        return None


def _uniquify(proxies: list[dict]) -> list[dict]:
    used: set[str] = set()
    out: list[dict] = []
    for i, proxy in enumerate(proxies):
        item = dict(proxy)
        name = str(item.get("name") or f"node-{i}").strip() or f"node-{i}"
        base = name
        n = 2
        while name in used:
            name = f"{base} #{n}"
            n += 1
        used.add(name)
        item["name"] = name
        out.append(item)
    return out


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _build_test_config(proxies: list[dict], controller_port: int, secret: str, mixed_port: int) -> dict:
    return {
        "mixed-port": mixed_port,
        "bind-address": "127.0.0.1",
        "allow-lan": False,
        "mode": "rule",
        "log-level": "error",
        "ipv6": False,
        "external-controller": f"127.0.0.1:{controller_port}",
        "secret": secret,
        "find-process-mode": "off",
        "geo-auto-update": False,
        "dns": {
            "enable": True,
            "ipv6": False,
            "enhanced-mode": "redir-host",
            "nameserver": ["223.5.5.5", "8.8.8.8"],
        },
        "proxies": proxies,
        "rules": ["MATCH,DIRECT"],
    }


def _tail_file(path: Path, limit: int = 500) -> str:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return text[-limit:].strip()


async def _protocol_filter(proxies: list[dict]) -> list[dict]:
    engine = find_mihomo()
    named = _uniquify(proxies)
    logger.info(
        f"开始协议测试: {len(named)} 个节点, 引擎={engine}, "
        f"并发={_PROTO_CONCURRENCY}, 超时={_PROTO_TIMEOUT}s, URL={PROBE_URL}"
    )
    delays = await _run_with_mihomo(engine, named)
    alive: list[tuple[float, dict]] = []
    handshake_fail = 0
    too_slow = 0
    for item in named:
        delay = delays.get(str(item["name"]))
        if delay is None:
            handshake_fail += 1
            continue
        if delay > _PROTO_MAX_MS:
            too_slow += 1
            continue
        alive.append((delay, item))
    alive.sort(key=lambda pair: pair[0])
    logger.info(
        f"协议测试完成: {len(alive)} 可用 / {too_slow} 延迟过高 / "
        f"{handshake_fail} 握手失败 / {len(named)} 总计"
    )
    return [item for _delay, item in alive]


async def _run_with_mihomo(engine: Path, named: list[dict]) -> dict[str, float | None]:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return await _run_once(engine, named)
        except KernelError as exc:
            last_error = exc
            logger.warning(f"筛选内核启动失败 (attempt {attempt + 1}/2): {exc}")
            await asyncio.sleep(0.3)
    raise last_error or KernelError("筛选内核启动失败")


async def _run_once(engine: Path, named: list[dict]) -> dict[str, float | None]:
    work_dir = Path(tempfile.mkdtemp(prefix="fq-sieve-"))
    proc: asyncio.subprocess.Process | None = None
    stdout_path = work_dir / "mihomo.out"
    stderr_path = work_dir / "mihomo.err"
    out_f = stdout_path.open("wb")
    err_f = stderr_path.open("wb")
    try:
        controller_port = _free_port()
        mixed_port = _free_port()
        secret = secrets.token_hex(16)
        config = _build_test_config(named, controller_port, secret, mixed_port)
        config_path = work_dir / "config.yaml"
        config_path.write_text(
            yaml.dump(config, allow_unicode=True, sort_keys=False, width=200),
            encoding="utf-8",
        )
        kwargs: dict = {}
        if sys.platform == "win32":
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        proc = await asyncio.create_subprocess_exec(
            str(engine),
            "-f",
            str(config_path),
            "-d",
            str(work_dir),
            stdout=out_f,
            stderr=err_f,
            cwd=str(work_dir),
            **kwargs,
        )
        await _wait_ready(proc, controller_port, secret, stderr_path)
        return await _delay_all(named, controller_port, secret)
    except KernelError:
        logger.error(f"筛选内核日志: {_tail_file(stderr_path)} {_tail_file(stdout_path)}")
        raise
    finally:
        await _stop_process(proc)
        for handle in (out_f, err_f):
            try:
                handle.close()
            except OSError:
                pass
        shutil.rmtree(work_dir, ignore_errors=True)


async def _wait_ready(
    proc: asyncio.subprocess.Process,
    port: int,
    secret: str,
    stderr_path: Path,
    timeout: float = 15.0,
) -> None:
    url = f"http://127.0.0.1:{port}/version"
    headers = {"Authorization": f"Bearer {secret}"}
    deadline = time.monotonic() + timeout
    async with httpx.AsyncClient(trust_env=False) as client:
        while time.monotonic() < deadline:
            if proc.returncode is not None:
                raise KernelError(
                    f"筛选内核提前退出 code={proc.returncode} stderr={_tail_file(stderr_path)}"
                )
            try:
                resp = await client.get(url, headers=headers, timeout=0.5)
                if resp.status_code == 200:
                    return
            except (httpx.HTTPError, OSError):
                pass
            await asyncio.sleep(0.1)
    raise KernelError(f"等待筛选内核超时 ({timeout}s) port={port}")


def _parse_delay(status_code: int, data: dict | None) -> float | None:
    if status_code != 200 or not isinstance(data, dict):
        return None
    delay = data.get("delay")
    if isinstance(delay, bool) or not isinstance(delay, (int, float)):
        return None
    if delay <= 0:
        return None
    return float(delay)


async def _delay_all(named: list[dict], controller_port: int, secret: str) -> dict[str, float | None]:
    headers = {"Authorization": f"Bearer {secret}"}
    timeout_ms = max(1, int(_PROTO_TIMEOUT * 1000))
    sem = asyncio.Semaphore(max(1, _PROTO_CONCURRENCY))
    async with httpx.AsyncClient(
        base_url=f"http://127.0.0.1:{controller_port}",
        headers=headers,
        timeout=_PROTO_TIMEOUT + 2.0,
        trust_env=False,
    ) as client:

        async def _one(name: str) -> tuple[str, float | None]:
            async with sem:
                encoded = quote(name, safe="")
                try:
                    resp = await client.get(
                        f"/proxies/{encoded}/delay",
                        params={"url": PROBE_URL, "timeout": timeout_ms},
                    )
                    try:
                        data = resp.json()
                    except ValueError:
                        data = None
                    return name, _parse_delay(resp.status_code, data if isinstance(data, dict) else None)
                except (httpx.HTTPError, OSError):
                    return name, None

        pairs = await asyncio.gather(*[_one(str(item["name"])) for item in named])
    return dict(pairs)


async def _stop_process(proc: asyncio.subprocess.Process | None) -> None:
    if proc is None or proc.returncode is not None:
        return
    proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except (asyncio.TimeoutError, OSError):
        proc.kill()
        try:
            await asyncio.wait_for(proc.wait(), timeout=3)
        except (asyncio.TimeoutError, OSError):
            pass
