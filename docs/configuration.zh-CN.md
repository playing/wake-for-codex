# 配置说明

[English](configuration.md)

Wake for Codex 不需要配置文件也能运行。需要自定义时，将
`config.example.json` 复制到仓库根目录并命名为 `config.json`。该本地文件已被
Git 忽略。

未知字段会报告完整配置路径并终止，不会被静默忽略。仓库中存在 `config.json` 时，
`doctor` 会自动使用它。

## 优先级

配置按以下顺序覆盖：

1. 命令行参数；
2. `config.json`；
3. 平台默认值。

配置文件中的相对路径以该配置文件所在目录为基准。

## 字段

| 字段 | 类型与范围 | 默认值 | 用途 |
|---|---|---:|---|
| `version` | 整数，当前为 `1` | 配置文件必填 | 配置 schema 版本 |
| `hotkeys.windows` | 热键字符串 | `ctrl+shift+g` | Windows Codex Voice Chat 热键 |
| `hotkeys.macos` | 热键字符串 | `ctrl+shift+g` | macOS Codex Voice Chat 热键 |
| `listener.device` | `null`、设备序号或设备名 | `null` | 默认或指定麦克风 |
| `listener.threshold` | `0.01`–`1.0` | `0.25` | 检测阈值；越高越严格 |
| `listener.score` | `0.1`–`10.0` | `1.0` | 关键词分数倍率 |
| `lifecycle.launchTimeoutSeconds` | `1`–`120` | `15` | 等待 Codex 接管麦克风的时间 |
| `lifecycle.sessionTimeoutSeconds` | `10`–`86400` | `14400` | Voice 会话观察上限 |
| `lifecycle.rearmDelaySeconds` | `0`–`60` | `1` | 恢复监听前的等待时间 |
| `lifecycle.errorRetryDelaySeconds` | `0.1`–`300` | `3` | 麦克风或初始化错误后的重试等待 |
| `macos.lifecycleMode` | `microphone` 或 `cooldown` | `microphone` | macOS Voice 生命周期策略 |
| `macos.cooldownSeconds` | `1`–`3600` | `30` | 仅 cooldown 模式使用的固定等待 |
| `paths.modelDir` | 路径或 `null` | 平台数据目录 | sherpa-onnx 模型目录 |
| `paths.phraseManifest` | 路径 | `launcher/phrases.json` | 可编辑唤醒词来源 |
| `paths.keywordsFile` | 路径 | `launcher/keywords.txt` | sherpa-onnx 编译关键词 |

## 热键

热键必须包含至少一个修饰键和一个普通按键：

```text
ctrl+shift+g
cmd+shift+g
alt+f8
```

支持 `ctrl`、`alt`/`option`、`shift`、`cmd`/`win`，以及 ASCII 字母、数字、
F1–F12、`Enter`、`Escape`、`Space` 和 `Tab`。

这里的热键必须与 **Codex → Settings → Voice → Voice Chat shortcut** 完全一致。
Wake for Codex 不读取或修改 Codex 设置。

## 麦克风

`null` 使用系统默认输入设备。查看可用设备：

```powershell
.\.venv-kws\Scripts\python.exe -c "import sounddevice as sd; print(sd.query_devices())"
```

```sh
./.venv-kws/bin/python -c 'import sounddevice as sd; print(sd.query_devices())'
```

将 `listener.device` 设为输出中的设备序号或完整名称。修改后运行 `doctor`。

## 灵敏度

建议从默认值开始。如果普通对话容易误唤醒，以 `0.30` 等小幅度提高
`listener.threshold`，然后用 `--dry-run --once` 验证。如果目标唤醒词经常漏检，
小幅降低阈值。阈值过低会明显增加误唤醒。

## macOS 生命周期

`microphone` 是推荐且已验证的模式。发送热键后等待默认输入设备变为活跃，并在
Codex Voice 结束、设备不再活跃时恢复监听。

`cooldown` 是 CoreAudio 状态不可靠时的备用模式。它不知道 Voice 何时真正结束，只
等待固定时间后恢复监听。等待时间应长于预期 Voice 会话，避免争用麦克风。

## 唤醒词

`launcher/phrases.json` 是人工编辑来源。每个条目包含：

- `label`：稳定的编译关键词标识；
- `spoken`：日志和文档中显示的文字；
- `raw`：sherpa-onnx 关键词文本，与 spoken 变体逐项对应。

修改后重新生成并验证两个关键词制品：

```powershell
.\.venv-kws\Scripts\python.exe -m launcher.sync_phrase_manifest `
  --write-raw --compile --verify-compiled-tokens
```

```sh
./.venv-kws/bin/python -m launcher.sync_phrase_manifest \
  --write-raw --compile --verify-compiled-tokens
```

短语制品失效或不同步时，Launcher 会拒绝初始化，不会静默使用另一组唤醒词。

## 命令行覆盖

Python 入口支持：

```text
--config
--device
--hotkey
--threshold
--score
--model-dir
--keywords-file
--phrase-manifest
--launch-timeout
--session-timeout
--rearm-delay
--error-retry-delay
--macos-lifecycle-mode
--macos-cooldown
```

使用 `python -m launcher.wake_launcher --help` 查看当前完整参数。
