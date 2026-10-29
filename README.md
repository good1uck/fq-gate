# fq-gate

一键全局翻墙。窗口一个大按钮；托盘左键打开窗口，右键连接 / 断开 / 退出。

## 下载

到 [Releases](https://github.com/good1uck/fq-gate/releases) 下载：

- Windows：[`fq-gate-setup.exe`](https://github.com/good1uck/fq-gate/releases/latest)（[v0.6.3](https://github.com/good1uck/fq-gate/releases/tag/v0.6.3)），双击安装。桌面会出现 **fq-gate**。第一次连接会要管理员权限，点允许。
- Android：[`fq-gate.apk`](https://github.com/good1uck/fq-gate/releases/tag/android-0.1.1)，拷到手机，允许未知来源后安装。打开后点「连接」，第一次会要 VPN 权限。

不要和 Clash、WARP 或其他 TUN / VPN 同时开。

卸载：系统设置 → 应用 → fq-gate，或双击 `%LOCALAPPDATA%\fq-gate\uninstall.bat`。

未签名，Windows 可能拦截，选「仍要运行」。

## 开发

`start.bat` 启动。重新打包：

```
powershell -NoProfile -ExecutionPolicy Bypass -File .\pack.ps1
```

产物是 `dist\fq-gate-setup.exe`。

## 已知限制

- 免费节点池，不稳定；后台大约每 30 分钟静默刷新。
- 全局模式，国内网站也会变慢。
- 程序本体没有在线升级地址（`config\channel.json` 的 `manifest_url` 为空）。
- 未签名，Windows 可能拦截，选「仍要运行」。
