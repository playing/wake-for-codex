"""Small interface for platform-specific Codex Voice Chat activation."""

from __future__ import annotations

from typing import Callable, Protocol


EventSink = Callable[..., None]


class VoiceChatNotObserved(TimeoutError):
    """Codex did not acquire the microphone before the launch deadline."""


class VoiceChatStateTimeout(TimeoutError):
    """Codex did not release the microphone before the safety deadline."""


class VoicePlatform(Protocol):
    def ready_details(self) -> dict[str, object]:
        """Return diagnostic details without triggering the hotkey."""

    def activate_and_wait(self, event_sink: EventSink) -> None:
        """Trigger Voice Chat, observe its lifecycle, and return after it ends."""
