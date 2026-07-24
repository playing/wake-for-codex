# Wake for Codex

> 唤醒 Codex，而不是再造一个语音助手。

[English](README.md)

[![CI](https://github.com/playing/wake-for-codex/actions/workflows/ci.yml/badge.svg)](https://github.com/playing/wake-for-codex/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> 非官方社区项目，与 OpenAI 无隶属关系，也未获得 OpenAI 背书。

Wake for Codex 是一个面向 Windows 和 macOS Codex Voice 的轻量、本地唤醒工具：

```text
本地唤醒词
→ 释放 Launcher 麦克风
→ 触发用户配置的 Codex Voice Chat 热键
→ Codex 接管对话、任务与权限
→ Voice 会话结束后恢复监听
```

它不转写、不粘贴、不发送 Prompt、不调用 OpenAI API、不读取 Codex 对话，也不会
批准权限请求。它不是第二个 Agent。

## 为什么做这个工具

Codex 已经负责完整的实时语音对话，本项目只补充缺少的免手操作入口：

- 使用 sherpa-onnx 在本地识别中文和英文唤醒词；
- Windows 与 macOS 共用一个小型核心；
- 只发送用户配置的热键，不做 UI 自动化；
- 不需要账户、API Key、云端音频、转写历史、Prompt 历史或统计服务；
- 可选 Codex SessionStart Hook 只负责启动单实例监听器。

## 当前状态

当前版本为 `v0.2.0`，变更记录见 [CHANGELOG.md](CHANGELOG.md)。

| 平台 | 状态 | 已验证范围 |
|---|---|---|
| Windows 10/11 | v0.2.0 | 本地 KWS、热键交接、Codex 麦克风生命周期、恢复监听、单实例、诊断、可选 Hook |
| macOS | v0.2.0 | 本地 KWS、CGEvent 热键交接、CoreAudio 生命周期、恢复监听、诊断、可选 cooldown |

旧 TypeWhisper Voice Bridge 不属于本项目。

## 环境要求

- Codex 桌面端，并在 **Settings → Voice** 中配置 Voice Chat 热键；
- Python 3.11 或 3.12（CI 实际覆盖的版本）；
- Windows 需要 PowerShell 7；
- 麦克风权限；
- macOS 需要为启动 Launcher 的进程授予辅助功能权限。

Wake for Codex 中配置的热键必须与 Codex Voice Chat 热键一致。

## 快速开始

### Windows

```powershell
git clone --branch v0.2.0 https://github.com/playing/wake-for-codex.git
Set-Location .\wake-for-codex
pwsh -NoProfile -File .\scripts\install-windows.ps1 -DownloadModel
pwsh -NoProfile -File .\run-wake-launcher.ps1 -Check
pwsh -NoProfile -File .\run-wake-launcher.ps1
```

### macOS

```sh
git clone --branch v0.2.0 https://github.com/playing/wake-for-codex.git
cd wake-for-codex
/bin/sh ./scripts/install-macos.sh --download-model
/bin/sh ./run-wake-launcher.sh --check
/bin/sh ./run-wake-launcher.sh
```

默认配置无需 `config.json` 即可运行。只有需要修改热键、麦克风、灵敏度、生命周期或
路径时，才复制 `config.example.json`。

macOS 首次运行前，请在
**系统设置 → 隐私与安全性 → 麦克风/辅助功能** 中允许启动脚本所使用的终端或
Launcher 进程。只读 `doctor` 会报告缺失的辅助功能授权，但不会替你修改系统权限。

## 升级

先停止后台 Launcher，获取并切换到目标 Release tag，重新运行对应平台安装器，再次
启动：

```text
git fetch --tags
git checkout v0.2.0
```

安装器会复用已有模型目录。只有仓库路径变化时，才需要重新安装可选 Hook。

## 默认唤醒词

- `Hey Codex`
- `你好 Codex`
- `OK Codex`

说出唤醒词，等待 Codex Voice Chat 接管麦克风，然后直接在 Codex 中继续对话。

唤醒词可以在 [`launcher/phrases.json`](launcher/phrases.json) 中修改。由于
sherpa-onnx 使用声学关键词检测，修改后必须重新编译：

```powershell
.\.venv-kws\Scripts\python.exe -m launcher.sync_phrase_manifest `
  --write-raw --compile --verify-compiled-tokens
```

```sh
./.venv-kws/bin/python -m launcher.sync_phrase_manifest \
  --write-raw --compile --verify-compiled-tokens
```

## 配置

`config.json` 是可选的，并已被 Git 忽略。可以从
[`config.example.json`](config.example.json) 开始：

```json
{
  "version": 1,
  "hotkeys": {
    "windows": "ctrl+shift+g",
    "macos": "ctrl+shift+g"
  },
  "listener": {
    "device": null,
    "threshold": 0.25,
    "score": 1.0
  },
  "macos": {
    "lifecycleMode": "microphone",
    "cooldownSeconds": 30
  }
}
```

支持至少一个修饰键加一个字母、数字、F1–F12、`Enter`、`Escape`、`Space` 或
`Tab`，例如 `ctrl+shift+g`、`cmd+shift+g`。

所有字段、命令行覆盖、唤醒词编译和生命周期模式见
[配置说明](docs/configuration.zh-CN.md)。

## 检查、测试与运行

只读环境检查：

```powershell
.\.venv-kws\Scripts\python.exe -m launcher.doctor
```

```sh
./.venv-kws/bin/python -m launcher.doctor
```

存在 `config.json` 时，`doctor` 会自动使用它，并报告实际配置文件、runtime import、
精确麦克风流格式、平台生命周期信号和可选 Hook 路径。

只检测一次唤醒词，不发送热键：

```powershell
pwsh -NoProfile -File .\run-wake-launcher.ps1 -DryRun -Once
```

```sh
/bin/sh ./run-wake-launcher.sh --dry-run --once
```

后台启动：

```powershell
pwsh -NoProfile -File .\start-wake-launcher.ps1
```

```sh
/bin/sh ./start-wake-launcher.sh
```

停止后台 Launcher：

```powershell
pwsh -NoProfile -File .\stop-wake-launcher.ps1
```

```sh
/bin/sh ./stop-wake-launcher.sh
```

## 可选 Codex Hook

可选 Hook 在 Codex `startup|resume` 时启动后台单实例。它不会接收 Prompt、分派任务
或参与执行。

安装：

```powershell
.\.venv-kws\Scripts\python.exe .\scripts\codex_hook.py `
  --repo-root (Get-Location)
```

```sh
./.venv-kws/bin/python ./scripts/codex_hook.py \
  --repo-root "$(pwd)"
```

安装器会合并 `~/.codex/hooks.json`、保留其他 Hook，并在替换已有文件前生成
`hooks.json.bak`。用户仍须在 Codex 内人工审核和信任；手动启动始终可用。

只卸载本项目 Hook：

```powershell
pwsh -NoProfile -File .\scripts\uninstall-hook.ps1
```

```sh
/bin/sh ./scripts/uninstall-hook.sh
```

## 常见问题

- **`doctor` 报告模型文件缺失：** 使用 `-DownloadModel` 或
  `--download-model` 重新运行安装器。
- **已识别唤醒词，但 Voice 没有打开：** 确认配置热键与 Codex Settings 完全一致，
  并且没有被系统或其他应用占用。
- **macOS 报告缺少辅助功能权限：** 将权限授予实际启动 Launcher 的终端或进程。
  Hook 启动与 Terminal 启动可能处于不同权限上下文。
- **误唤醒或漏唤醒：** 小幅调整 `listener.threshold`，使用
  `--dry-run --once` 验证。
- **出现 `already_running`：** 单实例保护正常；需要前台启动时先运行停止脚本。
- **可选 Hook 没有启动：** 先确认手动启动正常，再在 Codex 内审核并信任 Hook。

## 隐私与安全

Wake for Codex 只在本地处理麦克风帧，不保存原始录音。受限 JSON 日志只包含生命周期
事件：

- Windows：`%LOCALAPPDATA%\WakeForCodex\wake-launcher.jsonl`
- macOS：`~/Library/Application Support/WakeForCodex/wake-launcher.jsonl`

安全边界：

- 只发送用户配置的 Voice Chat 热键；
- 不查找输入框、不写剪贴板、不注入或自动发送 Prompt；
- 不自动批准 Codex 权限；
- 不保存转写、Prompt、对话、凭据或 API Key；
- 不建立账户、同步、记忆、统计或第二个 Agent。

安全问题报告和边界见 [SECURITY.md](SECURITY.md)。

## 模型说明

源代码采用 Apache-2.0。仓库和 Release 不提交、镜像或捆绑模型权重。安装器只从
sherpa-onnx 上游下载 KWS 模型并校验固定 SHA-256。上游尚未明确该模型制品的专属
许可证，使用前请阅读 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 开发验证

```powershell
.\.venv-kws\Scripts\python.exe -m pip install -r launcher\requirements.txt
.\.venv-kws\Scripts\python.exe -m compileall -q launcher scripts
.\.venv-kws\Scripts\python.exe -m launcher.self_test
.\.venv-kws\Scripts\python.exe -m launcher.sync_phrase_manifest
```

共享 Launcher 只通过很小的 `VoicePlatform` interface 访问操作系统。
Windows/macOS 的热键和麦克风生命周期实现分别位于 `windows_voice.py` 和
`macos_voice.py`。

## 许可证

[Apache License 2.0](LICENSE)
