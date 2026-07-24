"""Select the desktop adapter without importing another OS implementation."""

from __future__ import annotations

import sys

from .hotkey import HotkeySpec
from .voice_platform import VoicePlatform


def create_platform_adapter(
    *,
    hotkey: HotkeySpec,
    launch_timeout_seconds: float,
    session_timeout_seconds: float,
    macos_lifecycle_mode: str,
    macos_cooldown_seconds: float,
) -> VoicePlatform:
    if sys.platform == "win32":
        from .windows_voice import WindowsVoicePlatform

        return WindowsVoicePlatform(
            hotkey=hotkey,
            launch_timeout_seconds=launch_timeout_seconds,
            session_timeout_seconds=session_timeout_seconds,
        )
    if sys.platform == "darwin":
        from .macos_voice import MacOSVoicePlatform

        return MacOSVoicePlatform(
            hotkey=hotkey,
            launch_timeout_seconds=launch_timeout_seconds,
            session_timeout_seconds=session_timeout_seconds,
            lifecycle_mode=macos_lifecycle_mode,
            cooldown_seconds=macos_cooldown_seconds,
        )
    raise RuntimeError(f"Unsupported platform: {sys.platform}")
