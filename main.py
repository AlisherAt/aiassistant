"""Entry point for the Gold Trading AI Assistant."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from app.backtest.engine import BacktestEngine
from app.config import settings
from app.dashboard.html_dashboard import render_dashboard
from app.data.market_data import (
    fetch_dxy,
    fetch_economic_calendar,
    fetch_gold_ohlcv,
    fetch_real_yield,
)
from app.data.mt5_connector import fetch_live_gold_from_mt5
from app.notify.telegram_bot import TelegramBot
from app.orchestrator import TradingOrchestrator
from app.reporting.exporter import export_session_report
from app.risk.manager import PositionSizer, RiskManager
from app.scheduler.runner import Scheduler
from app.session.logger import SessionLogger
from app.trade.lifecycle import TradeLifecycle


def build_demo_dataframe():
    return pd.DataFrame(
        {
            "close": [100, 101, 102, 103, 104, 105, 106, 108, 109, 111, 113, 114],
            "high": [101, 102, 103, 104, 105, 106, 107, 109, 110, 112, 114, 115],
            "low": [99, 100, 101, 102, 103, 104, 105, 107, 108, 110, 112, 113],
        }
    )


def run_backtest_and_send_report(interval: str = "1h"):
    logger = SessionLogger()
    backtest = BacktestEngine(initial_balance=10000)
    df = fetch_gold_ohlcv(period="180d", interval=interval)
    summary = backtest.run(
        df,
        buy_threshold=0.7,
        sell_threshold=0.7,
        dxy=fetch_dxy(),
        real_yield=fetch_real_yield(settings.fred_api_key),
        timeframe=interval,
    )
    logger.log_event("backtest_summary", summary)
    report_path = export_session_report(summary, path="data/session_report.csv")
    dashboard_path = render_dashboard(summary, summary.get("equity_curve", []), path="data/dashboard.html")
    logger.dashboard_snapshot(summary)
    telegram = TelegramBot()
    msg = telegram.format_backtest_message(summary)
    msg = msg + f"\n\nCSV: {report_path}\nDashboard: {dashboard_path}"
    result = telegram.send_message(msg)
    return summary, result, report_path, dashboard_path


def run_real_time_market_scan():
    orchestrator = TradingOrchestrator()
    try:
        df = fetch_live_gold_from_mt5(settings.mt5_login, settings.mt5_password, settings.mt5_server)
        if df is None or df.empty:
            df = fetch_gold_ohlcv(period="90d", interval="1h")
            source = "yahoo_fallback"
        else:
            source = "mt5"
        event = fetch_economic_calendar(limit=1)[0] if fetch_economic_calendar(limit=1) else {"is_high_impact": False}
        result = orchestrator.analyze_market(df, dxy=fetch_dxy(), real_yield=fetch_real_yield(settings.fred_api_key), economic_event=event)
        result["data_source"] = source
        return result
    except Exception as exc:
        return {"error": str(exc), "data_source": "error"}


def main():
    parser = argparse.ArgumentParser(description="Gold Trading AI Assistant")
    parser.add_argument("--demo", action="store_true", help="Run a demo cycle")
    parser.add_argument("--json", action="store_true", help="Print JSON payload")
    parser.add_argument("--live", action="store_true", help="Run a live market snapshot cycle using free sources")
    parser.add_argument("--backtest", action="store_true", help="Run a historical backtest and send the summary to Telegram")
    parser.add_argument("--scan", action="store_true", help="Run immediate real-time gold market analysis")
    parser.add_argument("--schedule", action="store_true", help="Start scheduler for periodic backtest and market scan jobs")
    parser.add_argument("--interval", type=str, default="5m", help="Backtest interval: 5m, 15m, 1h, 4h, 1d")
    args = parser.parse_args()

    orchestrator = TradingOrchestrator()

    if args.schedule:
        scheduler = Scheduler(interval_seconds=1800)
        scheduler.start(lambda: run_backtest_and_send_report(interval=args.interval))
        print("Scheduler started. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            scheduler.stop()
        return

    if args.scan:
        result = run_real_time_market_scan()
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))

        telegram = TelegramBot()
        if "error" not in result:
            message = telegram.format_signal_message(
                {
                    "direction": result["ai_decision"]["direction"],
                    "confidence": result["ai_decision"]["confidence"],
                    "regime": result["market_regime"]["regime"],
                    "reasoning": result["ai_decision"]["reasoning"],
                    "data_source": result.get("data_source", "unknown"),
                    "russian_explanation": result["ai_decision"].get("russian_explanation"),
                }
            )
            print(telegram.send_message(message))
        return

    if args.backtest:
        summary, result, report_path, dashboard_path = run_backtest_and_send_report(interval=args.interval)
        if args.json:
            print(json.dumps({"summary": summary, "telegram": result, "csv": report_path, "dashboard": dashboard_path}, ensure_ascii=False, indent=2))
        else:
            print(summary)
            print(result)
        return

    if args.live:
        try:
            df = fetch_live_gold_from_mt5(settings.mt5_login, settings.mt5_password, settings.mt5_server)
            if df is None:
                df = fetch_gold_ohlcv(period="60d", interval="15m")
                source = "yahoo_fallback"
            else:
                source = "mt5"
            live_event = fetch_economic_calendar(limit=1)[0]
            result = orchestrator.analyze_market(
                df,
                dxy=fetch_dxy(),
                real_yield=fetch_real_yield(settings.fred_api_key),
                economic_event=live_event,
            )
            result["data_source"] = source
        except Exception as exc:
            print(f"Live data error: {exc}")
            return

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(result["ai_decision"])

        telegram = TelegramBot()
        message = telegram.format_signal_message(
            {
                "direction": result["ai_decision"]["direction"],
                "confidence": result["ai_decision"]["confidence"],
                "regime": result["market_regime"]["regime"],
                "reasoning": result["ai_decision"]["reasoning"],
                "data_source": result.get("data_source", "unknown"),
                "russian_explanation": result["ai_decision"].get("russian_explanation"),
            }
        )
        print(telegram.send_message(message))
        return

    df = build_demo_dataframe()
    result = orchestrator.analyze_market(df, dxy=98.5, real_yield=2.1, economic_event={"is_high_impact": False})
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"Regime: {result['market_regime']['regime']}")
        print(f"AI decision: {result['ai_decision']}")

    risk = RiskManager(account_balance=10000, risk_per_trade=0.005, max_daily_loss=0.02)
    position = PositionSizer(risk=risk, entry_price=105.0, stop_loss=103.0, lot_size=0.01)
    trade = TradeLifecycle(entry_price=105.0, stop_loss=103.0, take_profit=110.0, size=position.position_size())
    print(trade.exit_trade("tp_hit", price=110.2))

    telegram = TelegramBot()
    message = telegram.format_signal_message(
        {
            "direction": result["ai_decision"]["direction"],
            "confidence": result["ai_decision"]["confidence"],
            "regime": result["market_regime"]["regime"],
            "reasoning": result["ai_decision"]["reasoning"],
            "data_source": "demo",
            "russian_explanation": result["ai_decision"].get("russian_explanation"),
        }
    )
    print(telegram.send_message(message))


if __name__ == "__main__":
    main()
