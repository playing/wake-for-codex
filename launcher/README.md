# Wake for Codex internals

`wake_launcher.py` 是唯一运行入口。它隐藏 KWS、重试、单实例和事件日志，并只通过
`VoicePlatform` interface 调用平台行为。

## Modules

- `settings.py`：可选 JSON 配置、默认值和路径解析；
- `hotkey.py`：跨平台热键语法；
- `phrase_manifest.py`：唤醒词唯一人工来源；
- `model_config.py`：模型布局和平台数据目录；
- `platform_adapter.py`：只根据当前系统选择 adapter；
- `windows_voice.py`：SendInput 与 Codex microphone registry observer；
- `macos_voice.py`：CGEvent 与 CoreAudio default-input observer；
- `instance_lock.py`：Windows named mutex / macOS file lock；
- `event_log.py`：UTF-8 JSON 与 bounded rotation；
- `doctor.py`：只读环境诊断。

平台 adapter 的 interface 只有：

```python
ready_details() -> dict[str, object]
activate_and_wait(event_sink) -> None
```

主循环不读取注册表、CoreAudio、Quartz 或平台进程。

## Phrase compilation

`phrases.json`、`keywords_raw.txt` 和 `keywords.txt` 必须一致：

```powershell
.\.venv-kws\Scripts\python.exe -m launcher.sync_phrase_manifest `
  --write-raw --compile --verify-compiled-tokens
```

```sh
./.venv-kws/bin/python -m launcher.sync_phrase_manifest \
  --write-raw --compile --verify-compiled-tokens
```

## Events

状态以单行 JSON 输出：

- `ready`
- `listening`
- `wake_detected`
- `hotkey_sent`
- `voice_chat_active`
- `voice_chat_assumed_active`
- `voice_chat_ended`
- `rearming`
- `error`
- `already_running`
- `stopped`

日志不包含音频、转写、Prompt 或对话。

## Validation status

Windows 与 macOS 均已完成本地唤醒、热键交接、Voice Chat 生命周期和恢复监听的
真人闭环。Python 回归、短语一致性、模型探针、单实例和 `doctor` 检查通过。

本项目是小型 0.x 工具，不把长时间压力、所有声卡组合或所有 Codex 版本列为首发
门槛。睡眠恢复、设备切换和 Codex 更新后的行为作为已知兼容性边界持续回归。
