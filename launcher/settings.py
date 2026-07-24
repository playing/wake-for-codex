"""Validated optional configuration for the wake launcher."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .hotkey import HotkeySpec, parse_hotkey
from .model_config import default_model_dir


@dataclass(frozen=True)
class WakeSettings:
    model_dir: Path
    keywords_file: Path
    phrase_manifest: Path
    device: str | int | None
    threshold: float
    score: float
    hotkey: HotkeySpec
    launch_timeout_seconds: float
    session_timeout_seconds: float
    rearm_delay_seconds: float
    error_retry_delay_seconds: float
    macos_lifecycle_mode: str
    macos_cooldown_seconds: float


def _platform_name() -> str:
    if sys.platform == "win32":
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def _number(
    value: Any,
    *,
    name: str,
    minimum: float,
    maximum: float,
) -> float:
    result = float(value)
    if not minimum <= result <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return result


def _resolve_path(value: Any, base: Path, default: Path) -> Path:
    if value is None or str(value).strip() == "":
        return default
    path = Path(str(value)).expanduser()
    return path if path.is_absolute() else (base / path).resolve()


def _reject_unknown_fields(
    values: dict[str, Any],
    *,
    section: str | None,
    allowed: set[str],
) -> None:
    unknown = sorted(set(values) - allowed)
    if unknown:
        name = f"{section}.{unknown[0]}" if section else unknown[0]
        raise ValueError(f"Unknown configuration field: {name}")


def load_settings(
    *,
    root: Path,
    config_path: Path | None,
    overrides: dict[str, Any] | None = None,
) -> WakeSettings:
    document: dict[str, Any] = {}
    base = root
    if config_path is not None:
        resolved_config = config_path.expanduser().resolve()
        document = json.loads(resolved_config.read_text(encoding="utf-8"))
        if document.get("version") != 1:
            raise ValueError("Unsupported config version")
        _reject_unknown_fields(
            document,
            section=None,
            allowed={
                "version",
                "hotkeys",
                "listener",
                "lifecycle",
                "macos",
                "paths",
            },
        )
        base = resolved_config.parent

    listener = dict(document.get("listener") or {})
    _reject_unknown_fields(
        listener,
        section="listener",
        allowed={"device", "threshold", "score"},
    )
    lifecycle = dict(document.get("lifecycle") or {})
    _reject_unknown_fields(
        lifecycle,
        section="lifecycle",
        allowed={
            "launchTimeoutSeconds",
            "sessionTimeoutSeconds",
            "rearmDelaySeconds",
            "errorRetryDelaySeconds",
        },
    )
    paths = dict(document.get("paths") or {})
    _reject_unknown_fields(
        paths,
        section="paths",
        allowed={"modelDir", "keywordsFile", "phraseManifest"},
    )
    hotkeys = dict(document.get("hotkeys") or {})
    _reject_unknown_fields(
        hotkeys,
        section="hotkeys",
        allowed={"windows", "macos"},
    )
    macos = dict(document.get("macos") or {})
    _reject_unknown_fields(
        macos,
        section="macos",
        allowed={"lifecycleMode", "cooldownSeconds"},
    )
    values = dict(overrides or {})
    platform_name = _platform_name()

    default_hotkey = "ctrl+shift+g"
    hotkey_value = values.get("hotkey") or hotkeys.get(platform_name) or default_hotkey
    device = values.get("device")
    if device is None:
        device = listener.get("device")
    if isinstance(device, str) and device.isdigit():
        device = int(device)

    default_manifest = root / "phrases.json"
    default_keywords = root / "keywords.txt"
    return WakeSettings(
        model_dir=_resolve_path(
            values.get("model_dir", paths.get("modelDir")),
            base,
            default_model_dir(),
        ),
        keywords_file=_resolve_path(
            values.get("keywords_file", paths.get("keywordsFile")),
            base,
            default_keywords,
        ),
        phrase_manifest=_resolve_path(
            values.get("phrase_manifest", paths.get("phraseManifest")),
            base,
            default_manifest,
        ),
        device=device,
        threshold=_number(
            values.get("threshold", listener.get("threshold", 0.25)),
            name="listener.threshold",
            minimum=0.01,
            maximum=1.0,
        ),
        score=_number(
            values.get("score", listener.get("score", 1.0)),
            name="listener.score",
            minimum=0.1,
            maximum=10.0,
        ),
        hotkey=parse_hotkey(str(hotkey_value)),
        launch_timeout_seconds=_number(
            values.get(
                "launch_timeout",
                lifecycle.get("launchTimeoutSeconds", 15.0),
            ),
            name="lifecycle.launchTimeoutSeconds",
            minimum=1.0,
            maximum=120.0,
        ),
        session_timeout_seconds=_number(
            values.get(
                "session_timeout",
                lifecycle.get("sessionTimeoutSeconds", 14_400.0),
            ),
            name="lifecycle.sessionTimeoutSeconds",
            minimum=10.0,
            maximum=86_400.0,
        ),
        rearm_delay_seconds=_number(
            values.get(
                "rearm_delay",
                lifecycle.get("rearmDelaySeconds", 1.0),
            ),
            name="lifecycle.rearmDelaySeconds",
            minimum=0.0,
            maximum=60.0,
        ),
        error_retry_delay_seconds=_number(
            values.get(
                "error_retry_delay",
                lifecycle.get("errorRetryDelaySeconds", 3.0),
            ),
            name="lifecycle.errorRetryDelaySeconds",
            minimum=0.1,
            maximum=300.0,
        ),
        macos_lifecycle_mode=str(
            values.get(
                "macos_lifecycle_mode",
                macos.get("lifecycleMode", "microphone"),
            )
        ),
        macos_cooldown_seconds=_number(
            values.get(
                "macos_cooldown",
                macos.get("cooldownSeconds", 30.0),
            ),
            name="macos.cooldownSeconds",
            minimum=1.0,
            maximum=3_600.0,
        ),
    )
