# Layer 5 交接待测（豆包只测、不改代码）

豆包职责：跑命令行自测，把 `logs/selftest.json` 写入 `logs/layer5-result.md`。不要截 GUI、不要 OCR、不要开 `start.bat`、不要改源码、不要进 Layer 6。

窗口/托盘由用户自己另测。

测完：提醒用户打开 Clash Verge 的 TUN，然后把结果交给 Grok。

## 测前

1. 退出 VRChat。
2. Clash Verge：可先开「系统代理」，再关掉 TUN。
3. 若有 `-m src.main` 的 `python.exe`（GUI），先退出。
4. 不要杀命令行里不带 `fq-gate-` 的 `verge-mihomo.exe`（那是 Clash）。

## 豆包要跑的

```
D:\fq-gate\test.bat
```

可能弹 UAC，允许。等进程结束。读 `D:\fq-gate\logs\selftest.json`：

- `ok: true` → 通过（连接 + Grok 探测 + 网卡 fq-gate + 断开清理）
- `ok: false` → 失败，把 JSON 全文贴进结果

把 JSON 写入 `D:\fq-gate\logs\layer5-result.md` 即可，不要补 GUI 用例表。

## 不要做

- 不要改 `D:\fq-gate` 里的 py/yaml。
- 不要开 `start.bat`、不要截窗口。
- 不要关 Clash Verge 整个程序（只关 TUN）；测完必须让用户把 TUN 打开。
- 不要同时开 Clash TUN 和 fq-gate 连接。

## GUI / 托盘（用户自己测，豆包跳过）

`D:\fq-gate\start.bat`。状态可读 `logs/status.json` 的 `label`。
