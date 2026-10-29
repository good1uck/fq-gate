# 筛选交接待测（豆包只测、不改代码）

探测地址已改为 `https://grok.com/`。`http` / `socks` / `socks5` 也进筛选，能过 grok.com 就留。

不要截 GUI、不要 OCR、不要开 `start.bat`、不要改源码。

筛选 **不开 TUN**。Clash Verge 的 TUN 可以一直开着。

## 测前

1. 若有 `-m src.main` 的 `python.exe`（GUI），先退出。
2. 不要杀 Clash 自己的 `verge-mihomo.exe`。

## 豆包要跑的

```
D:\fq-gate\test-sieve.bat
```

可能要几分钟。等进程结束。读 `D:\fq-gate\logs\sieve.json`：

- `ok: true` 且 `alive` > 0 → 通过
- `ok: false` → 失败，把 JSON 全文贴进结果

把 JSON 写入 `D:\fq-gate\logs\sieve-result.md`。可以写上 `udp` / `other` / `elapsed_s`，不要自行解读为必须有 HY2。

## 不要做

- 不要改 `D:\fq-gate` 里的 py/yaml。
- 不要开 `start.bat`，不要跑 `test.bat`（那个会建 TUN，Grok 会掉）。
- 不要关 Clash Verge。

窗口仍由用户自己另测。
