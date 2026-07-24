"""Parse one configurable Voice Chat hotkey across desktop platforms."""

from __future__ import annotations

from dataclasses import dataclass


_MODIFIER_ALIASES = {
    "alt": "alt",
    "cmd": "cmd",
    "command": "cmd",
    "control": "ctrl",
    "ctrl": "ctrl",
    "meta": "cmd",
    "option": "alt",
    "shift": "shift",
    "win": "cmd",
    "windows": "cmd",
}
_MODIFIER_ORDER = ("ctrl", "alt", "shift", "cmd")
_KEY_ALIASES = {
    "esc": "escape",
    "return": "enter",
    "spacebar": "space",
}
_SPECIAL_KEYS = {"enter", "escape", "space", "tab"}


@dataclass(frozen=True)
class HotkeySpec:
    modifiers: tuple[str, ...]
    key: str

    @property
    def label(self) -> str:
        names = {
            "alt": "Alt",
            "cmd": "Cmd",
            "ctrl": "Ctrl",
            "shift": "Shift",
        }
        return "+".join([*(names[value] for value in self.modifiers), self.key.upper()])


def parse_hotkey(value: str) -> HotkeySpec:
    parts = [part.strip().lower() for part in value.split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("Hotkey must include at least one modifier and one key")

    modifiers: set[str] = set()
    keys: list[str] = []
    for part in parts:
        modifier = _MODIFIER_ALIASES.get(part)
        if modifier:
            modifiers.add(modifier)
        else:
            keys.append(_KEY_ALIASES.get(part, part))

    if len(keys) != 1:
        raise ValueError("Hotkey must contain exactly one non-modifier key")
    key = keys[0]
    is_alphanumeric = len(key) == 1 and key.isascii() and key.isalnum()
    is_function_key = (
        key.startswith("f")
        and key[1:].isdigit()
        and 1 <= int(key[1:]) <= 12
    )
    valid_key = is_alphanumeric or key in _SPECIAL_KEYS or is_function_key
    if not valid_key:
        raise ValueError(f"Unsupported hotkey key: {key!r}")

    ordered = tuple(name for name in _MODIFIER_ORDER if name in modifiers)
    if not ordered:
        raise ValueError("Hotkey must include at least one supported modifier")
    return HotkeySpec(modifiers=ordered, key=key)
