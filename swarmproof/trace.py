"""Journal d'exécution : événements machine-lisibles (trace.jsonl)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


class TraceWriter:
    """Accumule des événements horodatés puis les écrit en JSONL (une ligne par événement)."""

    def __init__(self) -> None:
        self.events: list[dict] = []

    def event(self, kind: str, **data: object) -> dict:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "event": kind,
        }
        record.update(data)
        self.events.append(record)
        return record

    def write(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as handle:
            for event in self.events:
                handle.write(json.dumps(event, ensure_ascii=False) + "\n")

    def count(self, kind: str) -> int:
        return sum(1 for event in self.events if event["event"] == kind)
