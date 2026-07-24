"""Read-only environment checks for Wake for Codex."""

from __future__ import annotations

import argparse
import importlib
import json
import sys
from collections.abc import Callable, Mapping
from pathlib import Path

import sounddevice as sd
from scripts.codex_hook import is_launcher_command, launcher_hook

from .model_config import ModelLayout
from .phrase_manifest import load_phrase_manifest, validate_keyword_artifacts
from .platform_adapter import create_platform_adapter
from .settings import load_settings


def result(name: str, status: str, detail: object) -> dict[str, object]:
    return {"name": name, "status": status, "detail": detail}


def resolve_config_path(repo_root: Path, requested: Path | None) -> Path | None:
    if requested is not None:
        return requested.expanduser().resolve()
    default = repo_root / "config.json"
    return default.resolve() if default.is_file() else None


def inspect_hook(hook_path: Path, repo_root: Path) -> dict[str, object]:
    if not hook_path.is_file():
        return result("hook", "optional", "not installed")
    try:
        document = json.loads(hook_path.read_text(encoding="utf-8"))
        groups = list((document.get("hooks") or {}).get("SessionStart") or [])
        commands = [
            command
            for group in groups
            if isinstance(group, dict)
            for command in list(group.get("hooks") or [])
            if isinstance(command, dict)
        ]
    except Exception as error:
        return result(
            "hook",
            "fail",
            {
                "file": str(hook_path),
                "reason": "invalid_hook_file",
                "error": str(error),
            },
        )

    expected = launcher_hook(repo_root.resolve())["hooks"][0]
    if any(
        command.get("command") == expected["command"]
        and command.get("commandWindows") == expected["commandWindows"]
        for command in commands
    ):
        return result("hook", "pass", {"file": str(hook_path)})
    if any(is_launcher_command(command) for command in commands):
        return result(
            "hook",
            "fail",
            {"file": str(hook_path), "reason": "stale_launcher_path"},
        )
    return result("hook", "optional", "not installed")


def inspect_microphone(
    device: str | int | None,
    *,
    format_checker: Callable[..., None] = sd.check_input_settings,
    device_reader: Callable[..., Mapping[str, object]] = sd.query_devices,
) -> dict[str, object]:
    try:
        format_checker(
            device=device,
            channels=1,
            dtype="float32",
            samplerate=16_000,
        )
        input_device = device_reader(device, "input")
        name = str(input_device["name"])
        return result(
            "microphone",
            "pass",
            {
                "device": name,
                "samplerate": 16_000,
                "channels": 1,
                "dtype": "float32",
            },
        )
    except Exception as error:
        return result("microphone", "fail", str(error))


def inspect_runtime(
    *,
    importer: Callable[[str], object] = importlib.import_module,
) -> dict[str, object]:
    try:
        versions: dict[str, str] = {}
        for name in ("sherpa_onnx", "numpy", "sounddevice"):
            module = importer(name)
            versions[name] = str(getattr(module, "__version__", "unknown"))
        return result("runtime", "pass", versions)
    except Exception as error:
        return result("runtime", "fail", str(error))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    repo_root = root.parent
    config_path = resolve_config_path(repo_root, args.config)
    checks: list[dict[str, object]] = []
    try:
        settings = load_settings(root=root, config_path=config_path)
        checks.append(
            result(
                "config",
                "pass",
                {
                    "file": str(config_path) if config_path else "defaults",
                    "hotkey": settings.hotkey.label,
                },
            )
        )
    except Exception as error:
        checks.append(result("config", "fail", str(error)))
        print(json.dumps({"status": "fail", "checks": checks}, ensure_ascii=True))
        return 1

    checks.append(inspect_runtime())

    model = ModelLayout(settings.model_dir)
    required_model_files = [
        model.tokens,
        model.encoder,
        model.decoder,
        model.joiner,
        model.english_lexicon,
    ]
    missing = [str(path) for path in required_model_files if not path.is_file()]
    checks.append(
        result(
            "model",
            "fail" if missing else "pass",
            missing if missing else str(settings.model_dir),
        )
    )

    try:
        definitions = load_phrase_manifest(settings.phrase_manifest)
        validate_keyword_artifacts(
            definitions,
            settings.phrase_manifest.with_name("keywords_raw.txt"),
            settings.keywords_file,
        )
        checks.append(
            result(
                "phrases",
                "pass",
                [phrase for item in definitions for phrase in item.spoken],
            )
        )
    except Exception as error:
        checks.append(result("phrases", "fail", str(error)))

    checks.append(inspect_microphone(settings.device))

    try:
        platform = create_platform_adapter(
            hotkey=settings.hotkey,
            launch_timeout_seconds=settings.launch_timeout_seconds,
            session_timeout_seconds=settings.session_timeout_seconds,
            macos_lifecycle_mode=settings.macos_lifecycle_mode,
            macos_cooldown_seconds=settings.macos_cooldown_seconds,
        )
        details = platform.ready_details()
        platform_status = (
            "fail"
            if sys.platform == "darwin"
            and not details.get("accessibility_trusted")
            else "pass"
        )
        checks.append(result("platform", platform_status, details))
    except Exception as error:
        checks.append(result("platform", "fail", str(error)))

    hook_path = Path.home() / ".codex" / "hooks.json"
    checks.append(inspect_hook(hook_path, repo_root))

    failed = any(check["status"] == "fail" for check in checks)
    print(
        json.dumps(
            {"status": "fail" if failed else "pass", "checks": checks},
            ensure_ascii=True,
            indent=2,
        )
    )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
