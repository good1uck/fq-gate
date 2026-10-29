# Layer 6 交付

朋友拿到的是一整个文件夹（或 zip），不是单独一个 exe。

## 给朋友

路径：`D:\fq-gate\dist\fq-gate-0.6.0.zip`  
或文件夹：`D:\fq-gate\dist\fq-gate`

1. 解压整个文件夹。
2. 双击 `install.bat`。
3. 桌面打开 **fq-gate**，点大按钮。第一次会要管理员权限。
4. 不要和 Clash / WARP 或其他 TUN 同时开。

卸载：`%LOCALAPPDATA%\fq-gate\uninstall.bat`

## 本机开发

`D:\fq-gate\start.bat`。不要从 Grok 拉 GUI。

命令行自测仍是 `D:\fq-gate\test.bat`（会关你这边的 Clash TUN）。

## 这层做了什么

- 自带 `vendor\mihomo.exe` + `wintun.dll`，不依赖 Clash Verge。
- 免费节点池静默拉取，界面不露订阅和 YAML。
- 后台约 30 分钟刷新节点。
- 安装到 `%LOCALAPPDATA%\fq-gate`，桌面和开始菜单快捷方式。
- 托盘：左键打开窗口，右键连接 / 断开 / 退出。

## 还没做

- 程序本体没有在线升级（`manifest_url` 为空）。节点会后台刷新。
- 未签名，SmartScreen 可能拦截。
- 免费池不稳定。
