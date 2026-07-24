"""Install or remove the optional user-level Codex SessionStart hook."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path
from typing import Any


def launcher_hook(repo_root: Path) -> dict[str, Any]:
    windows_start = repo_root / "start-wake-launcher.ps1"
    macos_start = repo_root / "start-wake-launcher.sh"
    return {
        "matcher": "startup|resume",
        "hooks": [
            {
                "type": "command",
                "command": f'/bin/sh "{macos_start.as_posix()}"',
                "commandWindows": (
                    'pwsh -NoProfile -NonInteractive -File '
                    f'"{windows_start}"'
                ),
                "timeout": 5,
                "statusMessage": "Starting Wake for Codex",
            }
        ],
    }


def is_launcher_command(hook: dict[str, Any]) -> bool:
    return any(
        "start-wake-launcher" in str(hook.get(name) or "")
        for name in ("command", "commandWindows")
    )


def remove_launcher_hooks(document: dict[str, Any]) -> bool:
    hooks = document.setdefault("hooks", {})
    groups = list(hooks.get("SessionStart") or [])
    changed = False
    retained_groups: list[dict[str, Any]] = []
    for group in groups:
        commands = list(group.get("hooks") or [])
        retained_commands = [
            command for command in commands if not is_launcher_command(command)
        ]
        if len(retained_commands) != len(commands):
            changed = True
        if retained_commands:
            updated = dict(group)
            updated["hooks"] = retained_commands
            retained_groups.append(updated)
    if retained_groups:
        hooks["SessionStart"] = retained_groups
    elif "SessionStart" in hooks:
        del hooks["SessionStart"]
    return changed


def install_launcher_hook(
    document: dict[str, Any],
    repo_root: Path,
) -> None:
    remove_launcher_hooks(document)
    hooks = document.setdefault("hooks", {})
    hooks.setdefault("SessionStart", []).append(launcher_hook(repo_root))


def write_document(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        shutil.copy2(path, path.with_name(f"{path.name}.bak"))
    payload = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(payload)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument(
        "--hooks-file",
        type=Path,
        default=Path.home() / ".codex" / "hooks.json",
    )
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hooks_file = args.hooks_file.expanduser().resolve()
    if hooks_file.is_file():
        document = json.loads(hooks_file.read_text(encoding="utf-8"))
    else:
        document = {"description": "User-level Codex hooks.", "hooks": {}}

    if args.uninstall:
        changed = remove_launcher_hooks(document)
        action = "removed" if changed else "not_installed"
    else:
        install_launcher_hook(document, args.repo_root.expanduser().resolve())
        action = "installed"

    if args.dry_run:
        print(json.dumps(document, ensure_ascii=False, indent=2))
        action = {
            "installed": "would_install",
            "removed": "would_remove",
            "not_installed": "would_remain_uninstalled",
        }[action]
    else:
        write_document(hooks_file, document)
    print(f"hook={action} file={hooks_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
