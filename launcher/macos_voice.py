"""macOS adapter for the Codex Voice Chat hotkey and microphone lifecycle."""

from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .hotkey import HotkeySpec
from .voice_platform import (
    EventSink,
    VoiceChatNotObserved,
    VoiceChatStateTimeout,
)


_APPLICATION_SERVICES = Path(
    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
)
_CORE_AUDIO = Path("/System/Library/Frameworks/CoreAudio.framework/CoreAudio")
_CORE_FOUNDATION = Path(
    "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
)
_AUDIO_OBJECT_SYSTEM = 1
_SCOPE_GLOBAL = int.from_bytes(b"glob", "big")
_ELEMENT_MAIN = 0
_DEFAULT_INPUT_DEVICE = int.from_bytes(b"dIn ", "big")
_DEVICE_RUNNING_SOMEWHERE = int.from_bytes(b"gone", "big")
_CG_HID_EVENT_TAP = 0
_CG_EVENT_FLAG_SHIFT = 1 << 17
_CG_EVENT_FLAG_CONTROL = 1 << 18
_CG_EVENT_FLAG_OPTION = 1 << 19
_CG_EVENT_FLAG_COMMAND = 1 << 20

_MAC_KEY_CODES = {
    "a": 0,
    "s": 1,
    "d": 2,
    "f": 3,
    "h": 4,
    "g": 5,
    "z": 6,
    "x": 7,
    "c": 8,
    "v": 9,
    "b": 11,
    "q": 12,
    "w": 13,
    "e": 14,
    "r": 15,
    "y": 16,
    "t": 17,
    "1": 18,
    "2": 19,
    "3": 20,
    "4": 21,
    "6": 22,
    "5": 23,
    "9": 25,
    "7": 26,
    "8": 28,
    "0": 29,
    "o": 31,
    "u": 32,
    "i": 34,
    "p": 35,
    "enter": 36,
    "l": 37,
    "j": 38,
    "k": 40,
    "n": 45,
    "m": 46,
    "tab": 48,
    "space": 49,
    "escape": 53,
    "f1": 122,
    "f2": 120,
    "f3": 99,
    "f4": 118,
    "f5": 96,
    "f6": 97,
    "f7": 98,
    "f8": 100,
    "f9": 101,
    "f10": 109,
    "f11": 103,
    "f12": 111,
}


class _AudioObjectPropertyAddress(ctypes.Structure):
    _fields_ = [
        ("mSelector", ctypes.c_uint32),
        ("mScope", ctypes.c_uint32),
        ("mElement", ctypes.c_uint32),
    ]


class CoreAudioInputUsage:
    def __init__(self) -> None:
        self._library = ctypes.cdll.LoadLibrary(str(_CORE_AUDIO))
        self._get_property = self._library.AudioObjectGetPropertyData
        self._get_property.argtypes = [
            ctypes.c_uint32,
            ctypes.POINTER(_AudioObjectPropertyAddress),
            ctypes.c_uint32,
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_void_p,
        ]
        self._get_property.restype = ctypes.c_int32

    def _uint32_property(self, object_id: int, selector: int) -> int:
        address = _AudioObjectPropertyAddress(
            mSelector=selector,
            mScope=_SCOPE_GLOBAL,
            mElement=_ELEMENT_MAIN,
        )
        value = ctypes.c_uint32()
        size = ctypes.c_uint32(ctypes.sizeof(value))
        status = self._get_property(
            object_id,
            ctypes.byref(address),
            0,
            None,
            ctypes.byref(size),
            ctypes.byref(value),
        )
        if status != 0:
            raise OSError(status, f"CoreAudio property failed: {selector:#x}")
        return int(value.value)

    def default_input_device(self) -> int:
        return self._uint32_property(_AUDIO_OBJECT_SYSTEM, _DEFAULT_INPUT_DEVICE)

    def active(self) -> bool:
        return bool(
            self._uint32_property(
                self.default_input_device(),
                _DEVICE_RUNNING_SOMEWHERE,
            )
        )


def accessibility_trusted() -> bool:
    library = ctypes.cdll.LoadLibrary(str(_APPLICATION_SERVICES))
    function = library.AXIsProcessTrusted
    function.argtypes = []
    function.restype = ctypes.c_bool
    return bool(function())


def macos_hotkey_values(hotkey: HotkeySpec) -> tuple[int, int]:
    key_code = _MAC_KEY_CODES.get(hotkey.key)
    if key_code is None:
        raise ValueError(f"Unsupported macOS hotkey key: {hotkey.key!r}")

    flags = 0
    if "shift" in hotkey.modifiers:
        flags |= _CG_EVENT_FLAG_SHIFT
    if "ctrl" in hotkey.modifiers:
        flags |= _CG_EVENT_FLAG_CONTROL
    if "alt" in hotkey.modifiers:
        flags |= _CG_EVENT_FLAG_OPTION
    if "cmd" in hotkey.modifiers:
        flags |= _CG_EVENT_FLAG_COMMAND
    return key_code, flags


def send_hotkey(hotkey: HotkeySpec) -> None:
    if not accessibility_trusted():
        raise PermissionError(
            "macOS Accessibility permission is required to send the Voice Chat hotkey"
        )
    key_code, flags = macos_hotkey_values(hotkey)

    library = ctypes.cdll.LoadLibrary(str(_APPLICATION_SERVICES))
    create_event = library.CGEventCreateKeyboardEvent
    create_event.argtypes = [ctypes.c_void_p, ctypes.c_uint16, ctypes.c_bool]
    create_event.restype = ctypes.c_void_p
    set_flags = library.CGEventSetFlags
    set_flags.argtypes = [ctypes.c_void_p, ctypes.c_uint64]
    set_flags.restype = None
    post_event = library.CGEventPost
    post_event.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
    post_event.restype = None
    core_foundation = ctypes.cdll.LoadLibrary(str(_CORE_FOUNDATION))
    release = core_foundation.CFRelease
    release.argtypes = [ctypes.c_void_p]
    release.restype = None

    for pressed in (True, False):
        event = create_event(None, key_code, pressed)
        if not event:
            raise RuntimeError("CGEventCreateKeyboardEvent failed")
        try:
            set_flags(event, flags)
            post_event(_CG_HID_EVENT_TAP, event)
        finally:
            release(event)


def wait_for_macos_voice_chat(
    *,
    launch_timeout_seconds: float,
    session_timeout_seconds: float,
    event_sink: EventSink,
    usage_reader: Callable[[], bool],
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    poll_seconds: float = 0.2,
) -> None:
    launch_deadline = monotonic() + launch_timeout_seconds
    while monotonic() < launch_deadline:
        if usage_reader():
            event_sink("voice_chat_active", microphone_scope="default_input")
            break
        sleep(poll_seconds)
    else:
        raise VoiceChatNotObserved("Codex Voice Chat did not acquire the microphone")

    session_deadline = monotonic() + session_timeout_seconds
    while monotonic() < session_deadline:
        if not usage_reader():
            event_sink("voice_chat_ended", microphone_scope="default_input")
            return
        sleep(poll_seconds)
    raise VoiceChatStateTimeout("Codex Voice Chat did not release the microphone")


@dataclass
class MacOSVoicePlatform:
    hotkey: HotkeySpec
    launch_timeout_seconds: float
    session_timeout_seconds: float
    lifecycle_mode: str
    cooldown_seconds: float

    def __post_init__(self) -> None:
        if self.lifecycle_mode not in {"microphone", "cooldown"}:
            raise ValueError(
                "macOS lifecycle mode must be 'microphone' or 'cooldown'"
            )

    def ready_details(self) -> dict[str, object]:
        details: dict[str, object] = {
            "platform": "macos",
            "hotkey": self.hotkey.label,
            "accessibility_trusted": accessibility_trusted(),
            "lifecycle_mode": self.lifecycle_mode,
        }
        if self.lifecycle_mode == "microphone":
            usage = CoreAudioInputUsage()
            details["default_input_device_id"] = usage.default_input_device()
        else:
            details["cooldown_seconds"] = self.cooldown_seconds
        return details

    def activate_and_wait(self, event_sink: EventSink) -> None:
        usage = (
            CoreAudioInputUsage()
            if self.lifecycle_mode == "microphone"
            else None
        )
        if usage is not None:
            release_deadline = time.monotonic() + 2.0
            while usage.active() and time.monotonic() < release_deadline:
                time.sleep(0.05)
            if usage.active():
                raise RuntimeError(
                    "Default input is still active after the wake listener released it"
                )

        send_hotkey(self.hotkey)
        event_sink("hotkey_sent", hotkey=self.hotkey.label)
        if usage is None:
            event_sink(
                "voice_chat_assumed_active",
                lifecycle_mode="cooldown",
                cooldown_seconds=self.cooldown_seconds,
            )
            time.sleep(self.cooldown_seconds)
            return
        wait_for_macos_voice_chat(
            launch_timeout_seconds=self.launch_timeout_seconds,
            session_timeout_seconds=self.session_timeout_seconds,
            event_sink=event_sink,
            usage_reader=usage.active,
        )
