"""Single source of truth for Wake Launcher phrases."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PhraseDefinition:
    label: str
    spoken: tuple[str, ...]
    raw: tuple[str, ...]


def load_phrase_manifest(path: Path) -> tuple[PhraseDefinition, ...]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("version") != 1:
        raise ValueError("Unsupported phrase manifest version")

    definitions: list[PhraseDefinition] = []
    seen_labels: set[str] = set()
    for item in document.get("phrases") or []:
        label = str(item.get("label") or "").strip()
        spoken = tuple(str(value).strip() for value in item.get("spoken") or [])
        raw = tuple(str(value).strip() for value in item.get("raw") or [])
        if not label or label in seen_labels:
            raise ValueError(f"Phrase labels must be unique and non-empty: {label!r}")
        if not spoken or len(spoken) != len(raw):
            raise ValueError(f"Phrase variants must align for label: {label}")
        if any(not value for value in (*spoken, *raw)):
            raise ValueError(f"Phrase variants must be non-empty for label: {label}")
        seen_labels.add(label)
        definitions.append(PhraseDefinition(label, spoken, raw))

    if not definitions:
        raise ValueError("Phrase manifest must define at least one wake phrase")
    return tuple(definitions)


def spoken_phrases(definitions: tuple[PhraseDefinition, ...]) -> list[str]:
    return [
        phrase
        for definition in definitions
        for phrase in definition.spoken
    ]


def raw_keyword_lines(definitions: tuple[PhraseDefinition, ...]) -> list[str]:
    return [
        f"{phrase} @{definition.label}"
        for definition in definitions
        for phrase in definition.raw
    ]


def compiled_keyword_labels(path: Path) -> list[str]:
    labels: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        before, separator, label = stripped.rpartition("@")
        if not separator or not before.strip() or not label.strip():
            raise ValueError(f"Invalid compiled keyword line: {line!r}")
        labels.append(label.strip())
    return labels


def expected_keyword_labels(definitions: tuple[PhraseDefinition, ...]) -> list[str]:
    return [
        definition.label
        for definition in definitions
        for _phrase in definition.raw
    ]


def validate_keyword_artifacts(
    definitions: tuple[PhraseDefinition, ...],
    raw_path: Path,
    compiled_path: Path,
) -> None:
    actual_raw = [line.strip() for line in raw_path.read_text(encoding="utf-8").splitlines()]
    if actual_raw != raw_keyword_lines(definitions):
        raise ValueError("keywords_raw.txt is out of sync with phrases.json")
    if compiled_keyword_labels(compiled_path) != expected_keyword_labels(definitions):
        raise ValueError("keywords.txt labels are out of sync with phrases.json")
