"""CSV export and session summary reporting utilities."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Any


def export_csv(rows: list[dict[str, Any]], path: str | Path = "data/session_report.csv") -> str:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    if not rows:
        rows = [{"timestamp": datetime.utcnow().isoformat(), "event": "no_data", "details": "No rows exported."}]

    fieldnames = sorted({key for row in rows for key in row.keys()})
    with file_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return str(file_path)


def export_session_report(summary: dict[str, Any], path: str | Path = "data/session_report.csv") -> str:
    row = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": "backtest_summary",
        "trades": summary.get("trades", 0),
        "total_return": summary.get("total_return", 0.0),
        "win_rate": summary.get("win_rate", 0.0),
        "profit": summary.get("profit", 0.0),
        "final_balance": summary.get("final_balance", 0.0),
        "best_trade": summary.get("best_trade", 0.0),
        "worst_trade": summary.get("worst_trade", 0.0),
    }
    if summary.get("equity_curve"):
        row["equity_curve"] = ";".join(f"{value:.2f}" for value in summary["equity_curve"])
    return export_csv([row], path=path)
