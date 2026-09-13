"""Generate a simple HTML dashboard with equity chart and metrics."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def render_dashboard(summary: dict[str, Any], equity_curve: list[float] | None = None, path: str = "data/dashboard.html") -> str:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    curve = equity_curve or [summary.get("final_balance", 10000.0)]
    labels = [str(i) for i in range(len(curve))]
    series_data = ", ".join(f"{value:.2f}" for value in curve)

    html = f"""
    <!doctype html>
    <html lang=\"en\">
      <head>
        <meta charset=\"utf-8\" />
        <title>Gold AI Dashboard</title>
        <style>
          body {{ font-family: Arial, sans-serif; margin: 24px; background: #0d1117; color: #e6edf3; }}
          .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 18px; margin-bottom: 20px; }}
          .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; }}
          .metric {{ padding: 14px; border-radius: 8px; background: #0f172a; border: 1px solid #334155; }}
          .chart {{ width: 100%; height: 220px; background: linear-gradient(180deg, #111827, #0d1117); border-radius: 8px; display: flex; align-items: end; gap: 4px; padding: 12px; }}
          .bar {{ flex: 1; background: linear-gradient(180deg, #38bdf8, #2563eb); border-radius: 4px 4px 0 0; min-width: 6px; }}
        </style>
      </head>
      <body>
        <div class=\"card\">
          <h1>Gold AI Trading Dashboard</h1>
          <div class=\"grid\">
            <div class=\"metric\"><b>Trades</b><br>{summary.get('trades', 0)}</div>
            <div class=\"metric\"><b>Total Return</b><br>{summary.get('total_return', 0.0)}%</div>
            <div class=\"metric\"><b>Win Rate</b><br>{summary.get('win_rate', 0.0)}%</div>
            <div class=\"metric\"><b>Profit</b><br>{summary.get('profit', 0.0)}</div>
            <div class=\"metric\"><b>Final Balance</b><br>{summary.get('final_balance', 0.0)}</div>
          </div>
        </div>

        <div class=\"card\">
          <h2>Equity Curve</h2>
          <div class=\"chart\">
            {''.join(f'<div class="bar" style="height: {((value / max(curve)) * 100) if max(curve) else 0}%"></div>' for value in curve)}
          </div>
        </div>

        <div class=\"card\">
          <h2>Summary</h2>
          <p>{summary.get('summary', 'Backtest completed.')}</p>
          <p>Generated at: {datetime.utcnow().isoformat()}</p>
        </div>
      </body>
    </html>
    """

    file_path.write_text(html, encoding="utf-8")
    return str(file_path)
