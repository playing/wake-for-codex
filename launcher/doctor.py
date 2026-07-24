"""Read-only environment checks for Wake for Codex."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import sounddevice as sd

from .model_config import ModelLayout
from .phrase_manifest import load_phrase_manifest, validate_keyword_artifacts
from .platform_adapter import create_platform_adapter
from .settings import load_settings


def result(name: str, status: str, detail: object) -> dict[str, object]:
    return {"name": name, "status": status, "detail": detail}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    checks: list[dict[str, object]] = []
    try:
        settings = load_settings(root=root, config_path=args.config)
        checks.append(result("config", "pass", settings.hotkey.label))
    except Exception as error:
        checks.append(result("config", "fail", str(error)))
        print(json.dumps({"status": "fail", "checks": checks}, ensure_ascii=True))
        return 1

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

    try:
        input_device = sd.query_devices(settings.device, "input")
        checks.append(result("microphone", "pass", input_device["name"]))
    except Exception as error:
        checks.append(result("microphone", "fail", str(error)))

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
    if not hook_path.is_file():
        checks.append(result("hook", "optional", "not installed"))
    else:
        text = hook_path.read_text(encoding="utf-8")
        checks.append(
            result(
                "hook",
                "pass" if "start-wake-launcher" in text else "optional",
                str(hook_path),
            )
        )

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
