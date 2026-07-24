"""Small lifecycle regression checks for Wake Launcher."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from .event_log import EventLogger
from .hotkey import parse_hotkey
from .macos_voice import (
    MacOSVoicePlatform,
    macos_hotkey_values,
    wait_for_macos_voice_chat,
)
from scripts.codex_hook import install_launcher_hook, remove_launcher_hooks
from .settings import load_settings
from .voice_platform import (
    VoiceChatNotObserved,
    VoiceChatStateTimeout,
)

if sys.platform == "win32":
    from .windows_voice import MicrophoneUsage, wait_for_voice_chat


class SequenceReader:
    def __init__(self, values: list[object]) -> None:
        self.values = values
        self.index = 0

    def __call__(self) -> object:
        value = self.values[min(self.index, len(self.values) - 1)]
        self.index += 1
        return value


class Clock:
    def __init__(self, step: float = 0.1) -> None:
        self.value = 0.0
        self.step = step

    def __call__(self) -> float:
        current = self.value
        self.value += self.step
        return current


@unittest.skipUnless(sys.platform == "win32", "Windows adapter test")
class WindowsVoiceLifecycleTests(unittest.TestCase):
    def test_active_session_ends(self) -> None:
        events: list[str] = []
        reader = SequenceReader(
            [
                MicrophoneUsage("Codex", 2, 1),
                MicrophoneUsage("Codex", 2, 2),
            ]
        )
        wait_for_voice_chat(
            baseline_start=1,
            launch_timeout_seconds=2,
            session_timeout_seconds=2,
            event_sink=lambda event, **_details: events.append(event),
            usage_reader=reader,
            monotonic=Clock(),
            sleep=lambda _seconds: None,
            poll_seconds=0,
        )
        self.assertEqual(events, ["voice_chat_active", "voice_chat_ended"])

    def test_stopped_launch_pulse_does_not_end_session(self) -> None:
        events: list[str] = []
        reader = SequenceReader(
            [
                MicrophoneUsage("Codex", 2, 2),
                MicrophoneUsage("Codex", 3, 2),
                MicrophoneUsage("Codex", 3, 3),
            ]
        )
        wait_for_voice_chat(
            baseline_start=1,
            launch_timeout_seconds=2,
            session_timeout_seconds=2,
            event_sink=lambda event, **_details: events.append(event),
            usage_reader=reader,
            monotonic=Clock(),
            sleep=lambda _seconds: None,
            poll_seconds=0,
        )
        self.assertEqual(events, ["voice_chat_active", "voice_chat_ended"])

    def test_launch_timeout_is_bounded(self) -> None:
        with self.assertRaises(VoiceChatNotObserved):
            wait_for_voice_chat(
                baseline_start=1,
                launch_timeout_seconds=0,
                session_timeout_seconds=2,
                event_sink=lambda *_args, **_kwargs: None,
            )

    def test_active_session_timeout_is_bounded(self) -> None:
        with self.assertRaises(VoiceChatStateTimeout):
            wait_for_voice_chat(
                baseline_start=1,
                launch_timeout_seconds=2,
                session_timeout_seconds=0,
                event_sink=lambda *_args, **_kwargs: None,
                usage_reader=lambda: MicrophoneUsage("Codex", 2, 1),
                monotonic=Clock(),
                sleep=lambda _seconds: None,
                poll_seconds=0,
            )


class MacOSVoiceLifecycleTests(unittest.TestCase):
    def test_active_session_ends(self) -> None:
        events: list[str] = []
        wait_for_macos_voice_chat(
            launch_timeout_seconds=2,
            session_timeout_seconds=2,
            event_sink=lambda event, **_details: events.append(event),
            usage_reader=SequenceReader([True, False]),
            monotonic=Clock(),
            sleep=lambda _seconds: None,
            poll_seconds=0,
        )
        self.assertEqual(events, ["voice_chat_active", "voice_chat_ended"])

    def test_launch_timeout_is_bounded(self) -> None:
        with self.assertRaises(VoiceChatNotObserved):
            wait_for_macos_voice_chat(
                launch_timeout_seconds=0,
                session_timeout_seconds=2,
                event_sink=lambda *_args, **_kwargs: None,
                usage_reader=lambda: False,
            )

    def test_active_session_timeout_is_bounded(self) -> None:
        with self.assertRaises(VoiceChatStateTimeout):
            wait_for_macos_voice_chat(
                launch_timeout_seconds=2,
                session_timeout_seconds=0,
                event_sink=lambda *_args, **_kwargs: None,
                usage_reader=lambda: True,
                monotonic=Clock(),
                sleep=lambda _seconds: None,
                poll_seconds=0,
            )

    def test_unknown_lifecycle_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            MacOSVoicePlatform(
                hotkey=parse_hotkey("ctrl+shift+g"),
                launch_timeout_seconds=2,
                session_timeout_seconds=2,
                lifecycle_mode="unknown",
                cooldown_seconds=30,
            )


class HotkeyTests(unittest.TestCase):
    def test_hotkey_is_normalized(self) -> None:
        hotkey = parse_hotkey("Control+Shift+g")
        self.assertEqual(hotkey.modifiers, ("ctrl", "shift"))
        self.assertEqual(hotkey.key, "g")
        self.assertEqual(hotkey.label, "Ctrl+Shift+G")

    def test_plain_key_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            parse_hotkey("g")

    def test_macos_mapping_for_default_hotkey(self) -> None:
        key_code, flags = macos_hotkey_values(parse_hotkey("ctrl+shift+g"))
        self.assertEqual(key_code, 5)
        self.assertNotEqual(flags, 0)


class SettingsTests(unittest.TestCase):
    def test_config_paths_are_relative_to_config(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "phrases.json").write_text("{}", encoding="utf-8")
            config = root / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "hotkeys": {
                            "windows": "ctrl+alt+k",
                            "macos": "ctrl+alt+k",
                        },
                        "paths": {"phraseManifest": "phrases.json"},
                    }
                ),
                encoding="utf-8",
            )
            settings = load_settings(root=root, config_path=config)
        self.assertEqual(settings.hotkey.label, "Ctrl+Alt+K")
        self.assertEqual(
            settings.phrase_manifest,
            (root / "phrases.json").resolve(),
        )

    def test_unknown_config_version_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.json"
            config.write_text(
                json.dumps({"version": 999}),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_settings(root=root, config_path=config)

    def test_unknown_config_field_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.json"
            config.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "listener": {"threshhold": 0.9},
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ValueError,
                r"Unknown configuration field: listener\.threshhold",
            ):
                load_settings(root=root, config_path=config)

    def test_unknown_fields_are_rejected_in_every_config_section(self) -> None:
        cases = [
            ({"mystery": True}, "mystery"),
            ({"hotkeys": {"linux": "ctrl+g"}}, "hotkeys.linux"),
            (
                {"lifecycle": {"launchTimeout": 10}},
                "lifecycle.launchTimeout",
            ),
            ({"paths": {"modelDirectory": "model"}}, "paths.modelDirectory"),
            ({"macos": {"cooldown": 30}}, "macos.cooldown"),
        ]
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.json"
            for fields, expected in cases:
                with self.subTest(field=expected):
                    config.write_text(
                        json.dumps({"version": 1, **fields}),
                        encoding="utf-8",
                    )
                    with self.assertRaisesRegex(
                        ValueError,
                        rf"Unknown configuration field: {expected}",
                    ):
                        load_settings(root=root, config_path=config)


class EventLogTests(unittest.TestCase):
    def test_log_rotates_before_exceeding_bound(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "events.jsonl"
            logger = EventLogger(path, max_bytes=80)
            logger.emit("first", value="x" * 30)
            logger.emit("second", value="y" * 30)
            self.assertTrue(path.is_file())
            self.assertTrue(path.with_name("events.jsonl.1").is_file())


class LauncherCliTests(unittest.TestCase):
    def test_startup_failure_is_written_to_the_event_log(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            config = root / "config.json"
            log_path = root / "events.jsonl"
            config.write_text('{"version": 999}', encoding="utf-8")

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "launcher.wake_launcher",
                    "--config",
                    str(config),
                    "--log-file",
                    str(log_path),
                    "--once",
                ],
                cwd=REPO_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )

            self.assertEqual(completed.returncode, 1)
            event = json.loads(log_path.read_text(encoding="utf-8"))
            self.assertEqual(event["event"], "error")
            self.assertEqual(event["kind"], "startup_failed")


class DoctorTests(unittest.TestCase):
    def test_repository_config_is_used_by_default(self) -> None:
        from .doctor import resolve_config_path

        with tempfile.TemporaryDirectory() as folder:
            repo_root = Path(folder)
            config = repo_root / "config.json"
            config.write_text('{"version": 1}', encoding="utf-8")
            self.assertEqual(resolve_config_path(repo_root, None), config.resolve())

    def test_hook_check_rejects_a_stale_launcher_path(self) -> None:
        from .doctor import inspect_hook

        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            hook_path = root / "hooks.json"
            document = {"hooks": {}}
            install_launcher_hook(document, root / "old-clone")
            hook_path.write_text(json.dumps(document), encoding="utf-8")

            check = inspect_hook(hook_path, root / "current-clone")

            self.assertEqual(check["status"], "fail")
            self.assertEqual(check["detail"]["reason"], "stale_launcher_path")

    def test_microphone_check_rejects_an_unsupported_runtime_format(self) -> None:
        from .doctor import inspect_microphone

        def reject_format(**_settings: object) -> None:
            raise ValueError("unsupported 16 kHz format")

        check = inspect_microphone(
            None,
            format_checker=reject_format,
            device_reader=lambda *_args: {"name": "Test microphone"},
        )

        self.assertEqual(check["status"], "fail")
        self.assertIn("unsupported 16 kHz format", str(check["detail"]))

    def test_runtime_check_reports_a_broken_kws_import(self) -> None:
        from .doctor import inspect_runtime

        def import_module(name: str) -> object:
            if name == "sherpa_onnx":
                raise ImportError("missing native runtime")
            return object()

        check = inspect_runtime(importer=import_module)

        self.assertEqual(check["status"], "fail")
        self.assertIn("missing native runtime", str(check["detail"]))


class CodexHookTests(unittest.TestCase):
    def test_install_is_idempotent_and_preserves_other_hooks(self) -> None:
        document = {
            "hooks": {
                "SessionStart": [
                    {
                        "matcher": "startup",
                        "hooks": [{"type": "command", "command": "other-command"}],
                    }
                ]
            }
        }
        install_launcher_hook(document, Path("/repo"))
        install_launcher_hook(document, Path("/repo"))
        groups = document["hooks"]["SessionStart"]
        launcher_commands = [
            hook
            for group in groups
            for hook in group["hooks"]
            if "start-wake-launcher" in str(hook)
        ]
        self.assertEqual(len(groups), 2)
        self.assertEqual(len(launcher_commands), 1)

    def test_uninstall_preserves_other_hooks(self) -> None:
        document = {"hooks": {}}
        install_launcher_hook(document, Path("/repo"))
        document["hooks"]["SessionStart"].append(
            {
                "matcher": "resume",
                "hooks": [{"type": "command", "command": "other-command"}],
            }
        )
        self.assertTrue(remove_launcher_hooks(document))
        self.assertEqual(
            document["hooks"]["SessionStart"][0]["hooks"][0]["command"],
            "other-command",
        )


if __name__ == "__main__":
    unittest.main()
