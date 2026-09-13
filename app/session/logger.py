"""Session recording for market events and dashboard snapshots."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class SessionLogger:
    def __init__(self, base_dir: str = "data/session"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def log_event(self, event: str, payload: dict | None = None):
        record = {
            "timestamp": datetime.utcnow().isoformat(),
            "event": event,
            "payload": payload or {},
        }
        log_file = self.base_dir / "session.log.jsonl"
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def dashboard_snapshot(self, summary: dict):
        snapshot = {
            "generated_at": datetime.utcnow().isoformat(),
            "summary": summary,
        }
        snapshot_file = self.base_dir / "dashboard.json"
        with snapshot_file.open("w", encoding="utf-8") as handle:
            json.dump(snapshot, handle, ensure_ascii=False, indent=2)
        return str(snapshot_file)
