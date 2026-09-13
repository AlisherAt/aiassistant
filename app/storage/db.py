"""SQLite storage for signal history and outcomes."""

import sqlite3
from pathlib import Path


class SignalStore:
    def __init__(self, db_path="data/signals.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                direction TEXT,
                confidence REAL,
                regime TEXT,
                summary TEXT,
                result TEXT DEFAULT 'pending'
            )
            """
        )
        conn.commit()
        conn.close()

    def add_signal(self, direction, confidence, regime, summary, result="pending"):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "INSERT INTO signals (timestamp, direction, confidence, regime, summary, result) VALUES (datetime('now'), ?, ?, ?, ?, ?)",
            (direction, confidence, regime, summary, result),
        )
        conn.commit()
        conn.close()

    def get_recent(self, limit=20):
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute(
            "SELECT timestamp, direction, confidence, regime, summary, result FROM signals ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        conn.close()
        return rows
