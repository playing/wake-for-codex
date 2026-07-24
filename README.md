# Wake for Codex

> Wake Codex, not another assistant.

[简体中文](README.zh-CN.md)

[![CI](https://github.com/playing/wake-for-codex/actions/workflows/ci.yml/badge.svg)](https://github.com/playing/wake-for-codex/actions/workflows/ci.yml)
[![License: Apache-2.0](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

> Unofficial community project. Not affiliated with or endorsed by OpenAI.

Wake for Codex is a small, local wake-word launcher for Codex Voice on Windows
and macOS:

```text
local wake word
→ release the launcher's microphone
→ press your configured Codex Voice Chat shortcut
→ let Codex own the conversation and permissions
→ re-arm when the Voice session ends
```

It does not transcribe, paste, send prompts, call the OpenAI API, read Codex
conversations, or approve permissions. It is not a second agent.

## Why this exists

Codex already provides the realtime conversation. This project adds only the
missing hands-free entry point:

- local Chinese and English keyword spotting with sherpa-onnx;
- Windows and macOS support from one small shared core;
- one configurable hotkey instead of UI automation;
- no account, API key, cloud audio, transcript, prompt history, or analytics;
- an optional Codex SessionStart Hook that only starts the singleton listener.

## Status

The current release is `v0.2.0`. See [CHANGELOG.md](CHANGELOG.md).

| Platform | Status | Verified scope |
|---|---|---|
| Windows 10/11 | v0.2.0 | Local KWS, hotkey handoff, Codex microphone lifecycle, re-arm, singleton, diagnostics, optional Hook |
| macOS | v0.2.0 | Local KWS, CGEvent hotkey handoff, CoreAudio lifecycle, re-arm, diagnostics, optional cooldown |

The legacy TypeWhisper Voice Bridge is not part of this project.

## Requirements

- Codex desktop with a Voice Chat shortcut configured in **Settings → Voice**;
- Python 3.11 or 3.12 (the versions exercised by CI);
- PowerShell 7 on Windows;
- Microphone permission;
- Accessibility permission on macOS for the process that starts the launcher.

The hotkey in Wake for Codex must match the Voice Chat hotkey configured in
Codex.

## Quick start

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

The defaults work without `config.json`. Copy `config.example.json` only when
you want to customize the hotkey, microphone, sensitivity, lifecycle, or paths.

Before the first macOS run, allow the terminal or launcher process under
**System Settings → Privacy & Security → Microphone** and
**Accessibility**. The read-only doctor reports missing Accessibility
permission but never changes it.

## Upgrade

Stop the background launcher, fetch the desired release tag, rerun the platform
installer, and start it again:

```text
git fetch --tags
git checkout v0.2.0
```

The installer reuses an existing verified model directory. Reinstall the
optional Hook only if the repository path changed.

## Default wake phrases

- `Hey Codex`
- `你好 Codex`
- `OK Codex`

Say a phrase, wait for Codex Voice Chat to acquire the microphone, and continue
the conversation in Codex.

Wake phrases are optional and editable in
[`launcher/phrases.json`](launcher/phrases.json). Because sherpa-onnx performs
acoustic keyword spotting, phrase changes must be compiled:

```powershell
.\.venv-kws\Scripts\python.exe -m launcher.sync_phrase_manifest `
  --write-raw --compile --verify-compiled-tokens
```

```sh
./.venv-kws/bin/python -m launcher.sync_phrase_manifest \
  --write-raw --compile --verify-compiled-tokens
```

## Configuration

`config.json` is optional and ignored by Git. Start from
[`config.example.json`](config.example.json):

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

The supported hotkey format is one or more modifiers plus a letter, number,
F1–F12, `Enter`, `Escape`, `Space`, or `Tab`. Examples:
`ctrl+shift+g`, `cmd+shift+g`.

See [Configuration](docs/configuration.md) for every field, command-line
override, phrase compilation, and lifecycle mode.

## Check, test, and run

Read-only environment check:

```powershell
.\.venv-kws\Scripts\python.exe -m launcher.doctor
```

```sh
./.venv-kws/bin/python -m launcher.doctor
```

`doctor` automatically uses the repository's `config.json` when present and
reports the effective file, runtime imports, exact microphone stream format,
platform lifecycle signal, and optional Hook path.

Detect one wake phrase without sending the hotkey:

```powershell
pwsh -NoProfile -File .\run-wake-launcher.ps1 -DryRun -Once
```

```sh
/bin/sh ./run-wake-launcher.sh --dry-run --once
```

Start in the background:

```powershell
pwsh -NoProfile -File .\start-wake-launcher.ps1
```

```sh
/bin/sh ./start-wake-launcher.sh
```

Stop the background launcher:

```powershell
pwsh -NoProfile -File .\stop-wake-launcher.ps1
```

```sh
/bin/sh ./stop-wake-launcher.sh
```

## Optional Codex Hook

The optional Hook starts the background singleton on Codex `startup|resume`.
It does not receive prompts, route tasks, or participate in execution.

Install:

```powershell
.\.venv-kws\Scripts\python.exe .\scripts\codex_hook.py `
  --repo-root (Get-Location)
```

```sh
./.venv-kws/bin/python ./scripts/codex_hook.py \
  --repo-root "$(pwd)"
```

The installer merges with `~/.codex/hooks.json`, preserves unrelated hooks,
and creates `hooks.json.bak` before replacing an existing file. Review and
trust the Hook manually in Codex. Manual launcher startup always remains
available.

Uninstall only this project's Hook:

```powershell
pwsh -NoProfile -File .\scripts\uninstall-hook.ps1
```

```sh
/bin/sh ./scripts/uninstall-hook.sh
```

## Troubleshooting

- **`doctor` reports missing model files:** rerun the installer with
  `-DownloadModel` or `--download-model`.
- **The wake phrase is detected but Voice does not open:** confirm that the
  configured hotkey exactly matches Codex Settings and is not claimed by the
  operating system or another app.
- **macOS reports missing Accessibility permission:** grant it to the terminal
  or process that actually starts the launcher. A Hook-launched process can
  have a different permission context from a Terminal-launched process.
- **False wakes or missed phrases:** adjust `listener.threshold` gradually and
  test with `--dry-run --once`.
- **`already_running`:** the singleton is healthy; use the stop script before
  starting another foreground copy.
- **The optional Hook does not start the listener:** verify manual startup
  first, then review and trust the Hook in Codex.

## Privacy and security

Wake for Codex processes microphone frames locally and does not save raw audio.
Its bounded JSON log contains only lifecycle events:

- Windows: `%LOCALAPPDATA%\WakeForCodex\wake-launcher.jsonl`
- macOS: `~/Library/Application Support/WakeForCodex/wake-launcher.jsonl`

Invariants:

- only the configured Voice Chat hotkey can be sent;
- no input-box discovery, clipboard write, prompt injection, or automatic send;
- no automatic Codex permission approval;
- no transcript, prompt, conversation, credential, or API key storage;
- no account, sync, memory, analytics, or second agent.

See [SECURITY.md](SECURITY.md) for reporting and security boundaries.

## Model notice

The source code is Apache-2.0. Model weights are not committed, mirrored, or
included in releases. Installers download the original sherpa-onnx KWS archive
and verify its pinned SHA-256. The upstream model-specific license is still
unclear; review [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) before use.

## Development

```powershell
.\.venv-kws\Scripts\python.exe -m pip install -r launcher\requirements.txt
.\.venv-kws\Scripts\python.exe -m compileall -q launcher scripts
.\.venv-kws\Scripts\python.exe -m launcher.self_test
.\.venv-kws\Scripts\python.exe -m launcher.sync_phrase_manifest
```

The shared launcher talks to the operating system only through the small
`VoicePlatform` interface. Platform-specific hotkey and microphone lifecycle
code lives in `windows_voice.py` and `macos_voice.py`.

## License

[Apache License 2.0](LICENSE)
