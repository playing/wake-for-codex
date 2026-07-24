"""Local wake-word launcher for Codex Voice Chat on Windows and macOS."""

from __future__ import annotations

import argparse
import queue
import time
from pathlib import Path
from typing import Any

import numpy as np
import sherpa_onnx
import sounddevice as sd

from .event_log import EventLogger
from .instance_lock import SingleInstance
from .model_config import ModelLayout
from .platform_adapter import create_platform_adapter
from .phrase_manifest import (
    load_phrase_manifest,
    spoken_phrases,
    validate_keyword_artifacts,
)
from .settings import WakeSettings, load_settings
from .voice_platform import (
    VoiceChatNotObserved,
    VoiceChatStateTimeout,
    VoicePlatform,
)


SAMPLE_RATE = 16_000
LOGGER = EventLogger()


def emit(event: str, **details: object) -> None:
    LOGGER.emit(event, **details)


def require_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(path)
    return str(path)


class KeywordListener:
    def __init__(
        self,
        model_dir: Path,
        keywords_file: Path,
        phrase_manifest: Path,
        device: str | int | None,
        threshold: float,
        score: float,
    ) -> None:
        definitions = load_phrase_manifest(phrase_manifest)
        validate_keyword_artifacts(
            definitions,
            phrase_manifest.with_name("keywords_raw.txt"),
            keywords_file,
        )
        self.phrases = spoken_phrases(definitions)
        self.device = device
        model = ModelLayout(model_dir.resolve())
        self.spotter = sherpa_onnx.KeywordSpotter(
            tokens=require_file(model.tokens),
            encoder=require_file(model.encoder),
            decoder=require_file(model.decoder),
            joiner=require_file(model.joiner),
            keywords_file=require_file(keywords_file),
            num_threads=1,
            keywords_score=score,
            keywords_threshold=threshold,
            provider="cpu",
        )

    def listen_once(self) -> str:
        audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=32)
        stream = self.spotter.create_stream()

        def audio_callback(
            indata: np.ndarray,
            frames: int,
            timing: object,
            status: object,
        ) -> None:
            del frames, timing
            if status:
                emit("audio_status", detail=str(status))
            samples = indata[:, 0].copy()
            try:
                audio_queue.put_nowait(samples)
            except queue.Full:
                try:
                    audio_queue.get_nowait()
                except queue.Empty:
                    pass
                audio_queue.put_nowait(samples)

        emit(
            "listening",
            phrases=self.phrases,
            device=self.device if self.device is not None else "default",
        )
        with sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=1_600,
            device=self.device,
            callback=audio_callback,
        ):
            while True:
                try:
                    samples = audio_queue.get(timeout=1.0)
                except queue.Empty as error:
                    raise RuntimeError(
                        "Microphone produced no audio for one second"
                    ) from error
                stream.accept_waveform(SAMPLE_RATE, samples)
                while self.spotter.is_ready(stream):
                    self.spotter.decode_stream(stream)
                    keyword = self.spotter.get_result(stream)
                    if keyword:
                        return keyword


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--log-file", type=Path)
    parser.add_argument("--model-dir", type=Path)
    parser.add_argument("--keywords-file", type=Path)
    parser.add_argument("--phrase-manifest", type=Path)
    parser.add_argument("--device", help="Input device index or name")
    parser.add_argument("--threshold", type=float)
    parser.add_argument("--score", type=float)
    parser.add_argument("--hotkey")
    parser.add_argument("--launch-timeout", type=float)
    parser.add_argument("--session-timeout", type=float)
    parser.add_argument("--rearm-delay", type=float)
    parser.add_argument("--error-retry-delay", type=float)
    parser.add_argument(
        "--macos-lifecycle-mode",
        choices=("microphone", "cooldown"),
    )
    parser.add_argument("--macos-cooldown", type=float)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def initialize_listener(
    settings: WakeSettings,
    platform: VoicePlatform,
) -> tuple[KeywordListener, dict[str, object], Any]:
    listener = KeywordListener(
        model_dir=settings.model_dir,
        keywords_file=settings.keywords_file.resolve(),
        phrase_manifest=settings.phrase_manifest.resolve(),
        device=settings.device,
        threshold=settings.threshold,
        score=settings.score,
    )
    platform_details = platform.ready_details()
    input_device = sd.query_devices(settings.device, "input")
    return listener, platform_details, input_device


def announce_ready(
    platform_details: dict[str, object],
    input_device: Any,
    dry_run: bool,
) -> None:
    emit(
        "ready",
        **platform_details,
        input_device=input_device["name"],
        dry_run=dry_run,
    )


def main() -> int:
    global LOGGER
    args = parse_args()
    LOGGER = EventLogger(args.log_file.expanduser().resolve() if args.log_file else None)
    root = Path(__file__).resolve().parent
    override_names = {
        "device",
        "error_retry_delay",
        "hotkey",
        "keywords_file",
        "launch_timeout",
        "macos_cooldown",
        "macos_lifecycle_mode",
        "model_dir",
        "phrase_manifest",
        "rearm_delay",
        "score",
        "session_timeout",
        "threshold",
    }
    try:
        settings = load_settings(
            root=root,
            config_path=args.config,
            overrides={
                name: getattr(args, name)
                for name in override_names
                if getattr(args, name) is not None
            },
        )
        platform = create_platform_adapter(
            hotkey=settings.hotkey,
            launch_timeout_seconds=settings.launch_timeout_seconds,
            session_timeout_seconds=settings.session_timeout_seconds,
            macos_lifecycle_mode=settings.macos_lifecycle_mode,
            macos_cooldown_seconds=settings.macos_cooldown_seconds,
        )
    except Exception as error:
        emit("error", kind="startup_failed", detail=str(error))
        return 1
    if args.check:
        _listener, platform_details, input_device = initialize_listener(
            settings,
            platform,
        )
        announce_ready(platform_details, input_device, args.dry_run)
        return 0

    with SingleInstance() as instance:
        if not instance.acquired:
            emit("already_running")
            return 0
        return run_launcher(args, settings, platform)


def run_launcher(
    args: argparse.Namespace,
    settings: WakeSettings,
    platform: VoicePlatform,
) -> int:
    try:
        listener: KeywordListener | None = None
        while True:
            if listener is None:
                try:
                    listener, platform_details, input_device = initialize_listener(
                        settings,
                        platform,
                    )
                    announce_ready(platform_details, input_device, args.dry_run)
                except Exception as error:
                    emit("error", kind="initialization_failed", detail=str(error))
                    if args.once:
                        return 1
                    emit(
                        "rearming",
                        delay_seconds=settings.error_retry_delay_seconds,
                    )
                    time.sleep(settings.error_retry_delay_seconds)
                    continue

            try:
                keyword = listener.listen_once()
            except Exception as error:
                listener = None
                emit("error", kind="microphone_listener_failed", detail=str(error))
                if args.once:
                    return 1
                emit(
                    "rearming",
                    delay_seconds=settings.error_retry_delay_seconds,
                )
                time.sleep(settings.error_retry_delay_seconds)
                continue

            emit("wake_detected", keyword=keyword, microphone_released=True)
            cycle_failed = False
            if args.dry_run:
                emit("dry_run_complete", hotkey=settings.hotkey.label)
            else:
                try:
                    platform.activate_and_wait(emit)
                except VoiceChatNotObserved as error:
                    cycle_failed = True
                    emit(
                        "error",
                        kind="voice_chat_not_observed",
                        detail=str(error),
                    )
                except VoiceChatStateTimeout as error:
                    cycle_failed = True
                    emit(
                        "error",
                        kind="voice_chat_state_timeout",
                        detail=str(error),
                    )
                except Exception as error:
                    cycle_failed = True
                    emit("error", kind="voice_chat_launch_failed", detail=str(error))

            if args.once:
                return 1 if cycle_failed else 0
            emit("rearming", delay_seconds=settings.rearm_delay_seconds)
            time.sleep(settings.rearm_delay_seconds)
    except KeyboardInterrupt:
        emit("stopped", reason="keyboard_interrupt")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
