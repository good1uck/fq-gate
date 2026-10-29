"""Silent free-pool fetch. Friends never see URLs."""

from __future__ import annotations

import re
import threading

import httpx
import yaml
from loguru import logger

from src.paths import nodes_file
from src.sieve import filter_alive, is_udp_proxy

_GITHUB_RAW_HOSTS = ("raw.githubusercontent.com", "github.com")
_RAW_GH_RE = re.compile(
    r"https?://raw\.githubusercontent\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/(?P<branch>[^/]+)/(?P<path>.+)"
)

_MIRRORS = [
    {"type": "prefix", "url": "https://gh-proxy.com/"},
    {"type": "jsdelivr", "url": "https://testingcf.jsdelivr.net"},
    {"type": "prefix", "url": "https://ghfast.top/"},
]

_SOURCES = [
    "https://raw.githubusercontent.com/peasoft/NoMoreWalls/master/list.meta.yml",
    "https://raw.githubusercontent.com/mfuu/v2ray/master/clash.yaml",
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/Eternity.yml",
]

_UA = "clash-verge/v2.4.5"
_LOCK = threading.Lock()


def _jsdelivr(base: str, raw_url: str) -> str | None:
    match = _RAW_GH_RE.match(raw_url)
    if not match:
        return None
    return (
        f"{base.rstrip('/')}/gh/{match.group('owner')}/{match.group('repo')}"
        f"@{match.group('branch')}/{match.group('path')}"
    )


def _targets(url: str) -> list[str]:
    if not any(host in url for host in _GITHUB_RAW_HOSTS):
        return [url]
    out: list[str] = []
    for mirror in _MIRRORS:
        if mirror["type"] == "jsdelivr":
            converted = _jsdelivr(mirror["url"], url)
            if converted:
                out.append(converted)
        else:
            out.append(mirror["url"].rstrip("/") + "/" + url)
    out.append(url)
    return out


def _fetch_text(url: str, timeout: float = 25.0) -> str | None:
    with httpx.Client(timeout=timeout, follow_redirects=True, headers={"User-Agent": _UA}, trust_env=False) as client:
        for target in _targets(url):
            try:
                resp = client.get(target)
                resp.raise_for_status()
                if resp.text and len(resp.text) > 50:
                    logger.info(f"池拉取成功 {len(resp.text)} bytes via {target[:48]}")
                    return resp.text
            except (httpx.HTTPError, OSError) as exc:
                logger.debug(f"池拉取失败 {target[:48]}: {exc}")
    return None


def _parse_proxies(text: str) -> list[dict]:
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError:
        return []
    if isinstance(data, dict):
        items = data.get("proxies") or []
    elif isinstance(data, list):
        items = data
    else:
        return []
    out: list[dict] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict) or not item.get("name") or not item.get("server"):
            continue
        key = f"{item.get('type')}|{item.get('server')}|{item.get('port')}"
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out


def refresh_pool(screen: bool = True) -> int:
    with _LOCK:
        return _refresh_pool_locked(screen=screen)


def _refresh_pool_locked(screen: bool) -> int:
    collected: list[dict] = []
    seen: set[str] = set()
    for url in _SOURCES:
        text = _fetch_text(url)
        if not text:
            continue
        for item in _parse_proxies(text):
            key = f"{item.get('type')}|{item.get('server')}|{item.get('port')}"
            if key in seen:
                continue
            seen.add(key)
            collected.append(item)
    udp_n = sum(1 for item in collected if is_udp_proxy(item))
    logger.info(
        f"池拉取 {len(collected)} 个 (HY2/TUIC 等 {udp_n} / 其他 {len(collected) - udp_n})"
    )
    if not collected:
        logger.warning("池刷新得到 0 个节点，保留旧缓存")
        return 0
    if screen:
        alive = filter_alive(collected)
        if not alive:
            logger.warning("筛选后 0 个节点，保留旧缓存")
            return 0
        collected = alive
    else:
        collected = [p for p in collected if is_udp_proxy(p)] + [
            p for p in collected if not is_udp_proxy(p)
        ]
    path = nodes_file()
    path.write_text(
        yaml.dump({"proxies": collected}, allow_unicode=True, sort_keys=False, width=200),
        encoding="utf-8",
    )
    logger.info(f"池已写入 {len(collected)} 个节点 screen={screen} -> {path}")
    return len(collected)
