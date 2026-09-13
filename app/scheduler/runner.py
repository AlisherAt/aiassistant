"""Simple scheduler for recurring backtest and market scan jobs."""

from __future__ import annotations

import threading
import time
from datetime import datetime
from typing import Any, Callable


class Scheduler:
    def __init__(self, interval_seconds: int = 3600):
        self.interval_seconds = int(interval_seconds)
        self._stop_event = threading.Event()
        self._thread = None

    def start(self, callback: Callable[[], Any]):
        def worker():
            while not self._stop_event.is_set():
                started_at = datetime.utcnow().isoformat()
                callback()
                print(f"[scheduler] run completed at {started_at}")
                self._stop_event.wait(self.interval_seconds)

        self._thread = threading.Thread(target=worker, daemon=True)
        self._thread.start()
        return self

    def stop(self):
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=2)
        return self
