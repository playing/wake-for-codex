"""Windows adapter for the Codex Voice Chat hotkey and microphone lifecycle."""

from __future__ import annotations

import ctypes
import time
import winreg
from ctypes import wintypes
from dataclasses import dataclass
from typing import Callable

from .hotkey import HotkeySpec
from .voice_platform import (
    EventSink,
    VoiceChatNotObserved,
    VoiceChatStateTimeout,
)


CODEX_MIC_PREFIX = "OpenAI.Codex_"
MICROPHONE_REGISTRY_PATH = (
    r"Software\Microsoft\Windows\CurrentVersion\CapabilityAccessManager"
    r"\ConsentStore\microphone"
)

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_ALT = 0x12
VK_LWIN = 0x5B
ULONG_PTR = ctypes.c_ulonglong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_ulong
_MODIFIER_KEYS = {
    "alt": VK_ALT,
    "cmd": VK_LWIN,
    "ctrl": VK_CONTROL,
    "shift": VK_SHIFT,
}
_SPECIAL_KEYS = {
    "enter": 0x0D,
    "escape": 0x1B,
    "space": 0x20,
    "tab": 0x09,
}


@dataclass(frozen=True)
class MicrophoneUsage:
    key_name: str
    started: int
    stopped: int

    @property
    def active(self) -> bool:
        return self.started > 0 and self.stopped < self.started


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", wintypes.WORD),
        ("wScan", wintypes.WORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class _HARDWAREINPUT(ctypes.Structure):
    _fields_ = [
        ("uMsg", wintypes.DWORD),
        ("wParamL", wintypes.WORD),
        ("wParamH", wintypes.WORD),
    ]


class _INPUTUNION(ctypes.Union):
    _fields_ = [
        ("mi", _MOUSEINPUT),
        ("ki", _KEYBDINPUT),
        ("hi", _HARDWAREINPUT),
    ]


class _INPUT(ctypes.Structure):
    _anonymous_ = ("value",)
    _fields_ = [("type", wintypes.DWORD), ("value", _INPUTUNION)]


def _registry_qword(key: winreg.HKEYType, name: str) -> int:
    try:
        value, _kind = winreg.QueryValueEx(key, name)
    except FileNotFoundError:
        return 0
    return int(value or 0)


def get_codex_microphone_usage() -> MicrophoneUsage:
    candidates: list[MicrophoneUsage] = []
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        MICROPHONE_REGISTRY_PATH,
        0,
        winreg.KEY_READ,
    ) as root:
        index = 0
        while True:
            try:
                name = winreg.EnumKey(root, index)
            except OSError:
                break
            index += 1
            if not name.startswith(CODEX_MIC_PREFIX):
                continue
            with winreg.OpenKey(root, name, 0, winreg.KEY_READ) as key:
                candidates.append(
                    MicrophoneUsage(
                        key_name=name,
                        started=_registry_qword(key, "LastUsedTimeStart"),
                        stopped=_registry_qword(key, "LastUsedTimeStop"),
                    )
                )

    if not candidates:
        raise RuntimeError("Codex microphone registry entry was not found")
    return max(candidates, key=lambda item: item.started)


def _keyboard_input(vk: int, key_up: bool = False) -> _INPUT:
    return _INPUT(
        type=INPUT_KEYBOARD,
        ki=_KEYBDINPUT(
            wVk=vk,
            wScan=0,
            dwFlags=KEYEVENTF_KEYUP if key_up else 0,
            time=0,
            dwExtraInfo=0,
        ),
    )


def _virtual_key(key: str) -> int:
    if len(key) == 1 and key.isascii() and key.isalnum():
        return ord(key.upper())
    if key in _SPECIAL_KEYS:
        return _SPECIAL_KEYS[key]
    if key.startswith("f") and key[1:].isdigit():
        return 0x70 + int(key[1:]) - 1
    raise ValueError(f"Unsupported Windows hotkey key: {key!r}")


def send_hotkey(hotkey: HotkeySpec) -> None:
    virtual_keys = [
        *(_MODIFIER_KEYS[name] for name in hotkey.modifiers),
        _virtual_key(hotkey.key),
    ]
    inputs = [
        *(_keyboard_input(vk) for vk in virtual_keys),
        *(_keyboard_input(vk, key_up=True) for vk in reversed(virtual_keys)),
    ]
    input_array = (_INPUT * len(inputs))(*inputs)
    sent = ctypes.windll.user32.SendInput(
        len(input_array),
        input_array,
        ctypes.sizeof(_INPUT),
    )
    if sent != len(input_array):
        raise ctypes.WinError(ctypes.get_last_error())


def wait_for_voice_chat(
    baseline_start: int,
    launch_timeout_seconds: float,
    session_timeout_seconds: float,
    event_sink: Callable[..., None],
    *,
    usage_reader: Callable[[], MicrophoneUsage] = get_codex_microphone_usage,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    poll_seconds: float = 0.2,
) -> None:
    launch_deadline = monotonic() + launch_timeout_seconds
    session_start = 0
    while monotonic() < launch_deadline:
        usage = usage_reader()
        if usage.started > baseline_start:
            session_start = usage.started
            if usage.active:
                event_sink("voice_chat_active", microphone_key=usage.key_name)
                break
            if usage.stopped >= usage.started:
                event_sink("voice_chat_ended", microphone_key=usage.key_name)
                return
        sleep(poll_seconds)

    if session_start == 0:
        raise VoiceChatNotObserved("Codex Voice Chat did not acquire the microphone")

    session_deadline = monotonic() + session_timeout_seconds
    while monotonic() < session_deadline:
        usage = usage_reader()
        if usage.started > session_start:
            session_start = usage.started
        if usage.stopped >= session_start:
            event_sink("voice_chat_ended", microphone_key=usage.key_name)
            return
        sleep(poll_seconds)

    raise VoiceChatStateTimeout(
        "Codex Voice Chat did not publish a stopped microphone state"
    )


@dataclass
class WindowsVoicePlatform:
    hotkey: HotkeySpec
    launch_timeout_seconds: float
    session_timeout_seconds: float

    def ready_details(self) -> dict[str, object]:
        usage = get_codex_microphone_usage()
        return {
            "platform": "windows",
            "hotkey": self.hotkey.label,
            "microphone_key": usage.key_name,
        }

    def activate_and_wait(self, event_sink: EventSink) -> None:
        baseline = get_codex_microphone_usage()
        send_hotkey(self.hotkey)
        event_sink("hotkey_sent", hotkey=self.hotkey.label)
        wait_for_voice_chat(
            baseline_start=baseline.started,
            launch_timeout_seconds=self.launch_timeout_seconds,
            session_timeout_seconds=self.session_timeout_seconds,
            event_sink=event_sink,
        )
