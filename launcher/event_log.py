"""UTF-8 JSON event output with one bounded rotated log file."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class EventLogger:
    def __init__(
        self,
        path: Path | None = None,
        max_bytes: int = 1024 * 1024,
    ) -> None:
        self.path = path
        self.max_bytes = max_bytes
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: str, **details: object) -> None:
        document = {
            "event": event,
            "at": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            **details,
        }
        print(json.dumps(document, ensure_ascii=True), flush=True)
        if self.path is None:
            return
        encoded = (
            json.dumps(document, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        if self.path.is_file() and self.path.stat().st_size + len(encoded) > self.max_bytes:
            previous = self.path.with_name(f"{self.path.name}.1")
            previous.unlink(missing_ok=True)
            self.path.replace(previous)
        with self.path.open("ab") as handle:
            handle.write(encoded)
