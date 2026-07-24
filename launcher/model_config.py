"""Shared sherpa-onnx model layout for runtime and probes."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


MODEL_NAME = "sherpa-onnx-kws-zipformer-zh-en-3M-2025-12-20"


@dataclass(frozen=True)
class ModelLayout:
    root: Path

    @property
    def tokens(self) -> Path:
        return self.root / "tokens.txt"

    @property
    def encoder(self) -> Path:
        return self.root / "encoder-epoch-13-avg-2-chunk-8-left-64.int8.onnx"

    @property
    def decoder(self) -> Path:
        return self.root / "decoder-epoch-13-avg-2-chunk-8-left-64.onnx"

    @property
    def joiner(self) -> Path:
        return self.root / "joiner-epoch-13-avg-2-chunk-8-left-64.int8.onnx"

    @property
    def english_lexicon(self) -> Path:
        return self.root / "en.phone"

    @property
    def test_wavs(self) -> Path:
        return self.root / "test_wavs"


def default_data_dir() -> Path:
    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if not local_app_data:
            raise RuntimeError("LOCALAPPDATA is not set")
        return Path(local_app_data) / "WakeForCodex"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "WakeForCodex"
    raise RuntimeError(f"Unsupported platform: {sys.platform}")


def default_model_dir() -> Path:
    configured = os.environ.get("CODEX_WAKE_MODEL_DIR")
    if configured:
        return Path(configured).expanduser()

    preferred = default_data_dir() / "models" / MODEL_NAME
    if preferred.is_dir():
        return preferred

    if sys.platform == "win32":
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            for legacy_name in ("CodexWakeLauncher", "CodexVoiceHelper"):
                legacy = (
                    Path(local_app_data)
                    / legacy_name
                    / "models"
                    / MODEL_NAME
                )
                if legacy.is_dir():
                    return legacy
    if sys.platform == "darwin":
        legacy = (
            Path.home()
            / "Library"
            / "Application Support"
            / "CodexWakeLauncher"
            / "models"
            / MODEL_NAME
        )
        if legacy.is_dir():
            return legacy
    return preferred
