"""Generate/check KWS raw keywords from the canonical phrase manifest."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from .model_config import ModelLayout, default_model_dir
from .phrase_manifest import (
    load_phrase_manifest,
    raw_keyword_lines,
    validate_keyword_artifacts,
)


def sherpa_cli() -> Path:
    executable = Path(sys.executable).resolve()
    suffix = ".exe" if sys.platform == "win32" else ""
    return executable.with_name(f"sherpa-onnx-cli{suffix}")


def compile_tokens(
    raw_path: Path,
    compiled_path: Path,
    model_dir: Path,
) -> None:
    cli = sherpa_cli()
    model = ModelLayout(model_dir)
    required = (cli, model.tokens, model.english_lexicon)
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError(
            "Keyword compilation dependencies are missing: " + ", ".join(missing)
        )

    completed = subprocess.run(
        [
            str(cli),
            "text2token",
            "--tokens",
            str(model.tokens),
            "--tokens-type",
            "phone+ppinyin",
            "--lexicon",
            str(model.english_lexicon),
            str(raw_path),
            str(compiled_path),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    if completed.returncode != 0 or not compiled_path.is_file():
        raise RuntimeError(
            "sherpa-onnx text2token failed: " + completed.stderr.strip()
        )


def verify_compiled_tokens(
    raw_path: Path,
    compiled_path: Path,
    model_dir: Path,
) -> None:
    """Rebuild model tokens and require the checked-in artifact to match."""
    with tempfile.TemporaryDirectory(prefix="CodexWake-tokencheck-") as folder:
        rebuilt_path = Path(folder) / "keywords.txt"
        compile_tokens(raw_path, rebuilt_path, model_dir)
        expected = compiled_path.read_text(encoding="utf-8-sig").splitlines()
        rebuilt = rebuilt_path.read_text(encoding="utf-8-sig").splitlines()
        if rebuilt != expected:
            raise ValueError(
                "keywords.txt token content is stale; rerun text2token after --write-raw"
            )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--raw", type=Path)
    parser.add_argument("--compiled", type=Path)
    parser.add_argument("--model-dir", type=Path, default=default_model_dir())
    parser.add_argument("--write-raw", action="store_true")
    parser.add_argument("--compile", action="store_true")
    parser.add_argument("--verify-compiled-tokens", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent
    manifest_path = (args.manifest or root / "phrases.json").resolve()
    raw_path = (args.raw or manifest_path.with_name("keywords_raw.txt")).resolve()
    compiled_path = (
        args.compiled or manifest_path.with_name("keywords.txt")
    ).resolve()
    definitions = load_phrase_manifest(manifest_path)

    if args.write_raw:
        raw_path.write_text(
            "\n".join(raw_keyword_lines(definitions)) + "\n",
            encoding="utf-8",
        )

    if args.compile:
        compile_tokens(raw_path, compiled_path, args.model_dir.resolve())

    validate_keyword_artifacts(definitions, raw_path, compiled_path)
    if args.verify_compiled_tokens:
        verify_compiled_tokens(raw_path, compiled_path, args.model_dir.resolve())
    print(
        f"phrase_manifest=pass labels={len(definitions)} "
        f"variants={len(raw_keyword_lines(definitions))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
