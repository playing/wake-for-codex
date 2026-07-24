# Changelog

## [0.2.0] - 2026-07-25

First public release of Wake for Codex.

### Included

- Local Chinese and English keyword spotting on Windows and macOS.
- Microphone release before the user-configured Codex Voice Chat hotkey.
- Voice-session lifecycle observation and automatic listener re-arm.
- Optional, merge-safe Codex `SessionStart` Hook.
- Read-only diagnostics, strict configuration validation, bounded JSON logs,
  and single-instance protection.
- Source-only distribution under Apache-2.0. Model weights remain upstream-only
  and are downloaded with a pinned SHA-256 check.

### Release hardening

- CI installs and imports the exact runtime dependencies on Windows and macOS
  with Python 3.11 and 3.12.
- The dependency set uses a NumPy version compatible with both supported Python
  versions.
- `doctor` uses the effective repository configuration, validates the KWS
  runtime and microphone stream format, and rejects a stale Hook path.
- Unknown configuration fields fail with their full path.
- Background startup failures are written to the structured event log.
