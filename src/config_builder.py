"""Build a strict-global Mihomo config. No split, no geosite, no UI-facing names."""

from __future__ import annotations

PROBE_URL = "https://grok.com/"


def _with_udp(proxy: dict) -> dict:
    item = dict(proxy)
    item.setdefault("udp", True)
    return item


def build_config(
    proxies: list[dict],
    *,
    controller_port: int,
    mixed_port: int,
    secret: str,
) -> dict:
    prepared = []
    used: set[str] = set()
    for i, proxy in enumerate(proxies):
        item = _with_udp(proxy)
        name = str(item.get("name") or f"node-{i}").strip() or f"node-{i}"
        base = name
        n = 2
        while name in used:
            name = f"{base} #{n}"
            n += 1
        used.add(name)
        item["name"] = name
        prepared.append(item)
    names = [p["name"] for p in prepared]
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
        "unified-delay": True,
        "tun": {
            "enable": True,
            "stack": "system",
            "device": "fq-gate",
            "auto-route": True,
            "auto-detect-interface": True,
            "strict-route": False,
            "dns-hijack": ["any:53", "tcp://any:53"],
            "mtu": 1400,
        },
        "dns": {
            "enable": True,
            "ipv6": False,
            "enhanced-mode": "fake-ip",
            "fake-ip-range": "198.18.0.1/16",
            "fake-ip-filter": ["*.lan", "*.local", "localhost", "*.localhost"],
            "default-nameserver": ["223.5.5.5", "119.29.29.29"],
            "nameserver": [
                "https://dns.google/dns-query",
                "https://1.1.1.1/dns-query",
            ],
            "proxy-server-nameserver": ["223.5.5.5", "119.29.29.29"],
        },
        "sniffer": {
            "enable": True,
            "parse-pure-ip": True,
            "override-destination": True,
            "sniff": {
                "HTTP": {"ports": [80, 8080]},
                "TLS": {"ports": [443, 8443]},
            },
        },
        "proxies": prepared,
        "proxy-groups": [
            {
                "name": "GLOBAL",
                "type": "url-test",
                "url": PROBE_URL,
                "interval": 30,
                "tolerance": 200,
                "lazy": False,
                "timeout": 8000,
                "expected-status": "204",
                "proxies": names,
            }
        ],
        # 仍是整机进隧道。丢掉 UDP/443（QUIC）好让 Chrome 回落到 TCP，grok.com 才过得去。
        "rules": [
            "AND,((NETWORK,udp),(DST-PORT,443)),REJECT",
            "MATCH,GLOBAL",
        ],
    }
