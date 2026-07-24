# Configuration

[简体中文](configuration.zh-CN.md)

Wake for Codex works without a configuration file. To customize it, copy
`config.example.json` to the repository root as `config.json`. The local file is
ignored by Git.

## Precedence

Values are resolved in this order:

1. command-line option;
2. `config.json`;
3. platform default.

Relative paths in a configuration file are resolved from that file's directory.

## Fields

| Field | Type and range | Default | Purpose |
|---|---|---:|---|
| `version` | integer, currently `1` | required in a file | Configuration schema version |
| `hotkeys.windows` | hotkey string | `ctrl+shift+g` | Codex Voice Chat shortcut on Windows |
| `hotkeys.macos` | hotkey string | `ctrl+shift+g` | Codex Voice Chat shortcut on macOS |
| `listener.device` | `null`, device index, or device name | `null` | Default or selected microphone |
| `listener.threshold` | `0.01`–`1.0` | `0.25` | Detection threshold; higher is stricter |
| `listener.score` | `0.1`–`10.0` | `1.0` | Keyword score multiplier |
| `lifecycle.launchTimeoutSeconds` | `1`–`120` | `15` | Time allowed for Codex to acquire the microphone |
| `lifecycle.sessionTimeoutSeconds` | `10`–`86400` | `14400` | Maximum observed Voice session |
| `lifecycle.rearmDelaySeconds` | `0`–`60` | `1` | Delay before listening resumes |
| `lifecycle.errorRetryDelaySeconds` | `0.1`–`300` | `3` | Retry delay after a microphone or initialization error |
| `macos.lifecycleMode` | `microphone` or `cooldown` | `microphone` | macOS Voice lifecycle strategy |
| `macos.cooldownSeconds` | `1`–`3600` | `30` | Fixed delay used only by cooldown mode |
| `paths.modelDir` | path or `null` | platform data directory | sherpa-onnx model directory |
| `paths.phraseManifest` | path | `launcher/phrases.json` | Editable wake-phrase source |
| `paths.keywordsFile` | path | `launcher/keywords.txt` | Compiled sherpa-onnx keywords |

## Hotkeys

A hotkey requires one or more modifiers and exactly one key:

```text
ctrl+shift+g
cmd+shift+g
alt+f8
```

Supported modifiers are `ctrl`, `alt`/`option`, `shift`, and `cmd`/`win`.
Supported keys are ASCII letters, digits, F1–F12, `Enter`, `Escape`, `Space`,
and `Tab`.

The configured hotkey must exactly match **Codex → Settings → Voice → Voice
Chat shortcut**. Wake for Codex does not inspect or change Codex settings.

## Microphone

`null` uses the operating system's default input device. To inspect devices:

```powershell
.\.venv-kws\Scripts\python.exe -c "import sounddevice as sd; print(sd.query_devices())"
```

```sh
./.venv-kws/bin/python -c 'import sounddevice as sd; print(sd.query_devices())'
```

Set `listener.device` to the printed numeric index or exact device name. Run
`doctor` after changing the device.

## Sensitivity

Start with the defaults. If unrelated speech wakes the launcher, increase
`listener.threshold` in small increments such as `0.30`, then use
`--dry-run --once`. If the intended phrase is frequently missed, lower it in
small increments. Extremely low thresholds make false wakes more likely.

## macOS lifecycle

`microphone` is the recommended and verified mode. It waits for the default
input device to become active after the hotkey and inactive when Codex Voice
ends.

`cooldown` is a fallback for systems where CoreAudio activity is ambiguous. It
does not claim to know when Voice ends; it waits the configured number of
seconds before listening again. Set a cooldown longer than the expected Voice
session to avoid microphone competition.

## Wake phrases

`launcher/phrases.json` is the human-edited source. Each entry contains:

- `label`: stable compiled keyword identifier;
- `spoken`: text shown in logs and documentation;
- `raw`: sherpa-onnx keyword text, one item aligned with each spoken variant.

After editing, regenerate and verify both keyword artifacts:

```powershell
.\.venv-kws\Scripts\python.exe -m launcher.sync_phrase_manifest `
  --write-raw --compile --verify-compiled-tokens
```

```sh
./.venv-kws/bin/python -m launcher.sync_phrase_manifest \
  --write-raw --compile --verify-compiled-tokens
```

Invalid or stale phrase artifacts stop initialization instead of silently
running with a different phrase set.

## Command-line overrides

The Python entry point supports:

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

Use `python -m launcher.wake_launcher --help` for the current full list.
