"""Simple but useful event-driven backtest engine for the gold AI assistant."""

from __future__ import annotations

from typing import Any

import pandas as pd

from app.ai.arbiter import AIArbiter
from app.regime.market_regime import classify_market_regime
from app.strategies.correlation import analyze as analyze_correlation
from app.strategies.ict_smc import analyze as analyze_ict_smc
from app.strategies.trend_following import analyze as analyze_trend_following


class BacktestEngine:
    def __init__(self, initial_balance: float = 10000.0):
        self.initial_balance = float(initial_balance)

    @staticmethod
    def _true_range(df: pd.DataFrame) -> pd.Series:
        high = df["high"].astype(float)
        low = df["low"].astype(float)
        close = df["close"].astype(float)
        prev_close = close.shift(1).fillna(close)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ], axis=1).max(axis=1)
        return tr.fillna(0.0)

    @staticmethod
    def _atr(df: pd.DataFrame, period: int = 14) -> float:
        if df is None or df.empty or len(df) < period:
            return 0.0
        return float(BacktestEngine._true_range(df).rolling(period).mean().iloc[-1])

    @staticmethod
    def _calculate_levels(df: pd.DataFrame, direction: str, sl_multiplier: float = 1.5, rr_ratio: float = 2.0):
        atr = BacktestEngine._atr(df, period=14)
        current_price = float(df["close"].astype(float).iloc[-1])
        sl_distance = atr * sl_multiplier if atr > 0 else max(current_price * 0.0015, 1.5)
        tp_distance = sl_distance * rr_ratio

        if direction == "buy":
            stop = current_price - sl_distance
            take_profit = current_price + tp_distance
        else:
            stop = current_price + sl_distance
            take_profit = current_price - tp_distance

        return {
            "stop": stop,
            "take_profit": take_profit,
            "sl_distance": sl_distance,
            "tp_distance": tp_distance,
            "atr": atr,
        }

    @staticmethod
    def _resample_window(df: pd.DataFrame, rule: str) -> pd.DataFrame:
        if df is None or df.empty:
            return pd.DataFrame()
        working = df.copy()
        if "timestamp" not in working.columns:
            if isinstance(working.index, pd.DatetimeIndex):
                working = working.reset_index().rename(columns={"index": "timestamp"})
            else:
                working["timestamp"] = pd.to_datetime(working.index)
        working = working.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
        if {"open", "high", "low", "close"}.issubset(working.columns):
            out = (
                working.set_index("timestamp")
                .resample(rule)
                .agg({
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                })
                .dropna()
                .reset_index()
                .rename(columns={"index": "timestamp"})
            )
            return out
        return working

    def _evaluate_signal(self, df: pd.DataFrame, dxy: float | None = None, real_yield: float | None = None):
        regime = classify_market_regime(df)
        df_5m = df.copy() if df is not None else pd.DataFrame()
        df_15m = self._resample_window(df_5m, "15min")
        df_1h = self._resample_window(df_5m, "1h")
        signals = [
            analyze_trend_following(df_1h, df_15m, df_5m),
            analyze_ict_smc(df_15m, df_5m),
            analyze_correlation(df_5m, dxy=dxy, real_yield=real_yield),
        ]
        context = AIArbiter.build_context(signals, regime=regime)
        decision = AIArbiter.decide(context)
        return decision, regime, signals

    @staticmethod
    def _resolve_exit_from_bar(position: dict[str, Any], bar: pd.Series) -> tuple[float | None, str | None]:
        side = position["side"]
        entry = float(position["entry"])
        stop = float(position["stop"])
        take_profit = float(position["take_profit"])
        size = float(position.get("size", 1.0))
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])

        if side == "buy":
            if bar_low <= stop:
                return (stop - entry) * size, "sl_hit"
            if bar_high >= take_profit:
                return (take_profit - entry) * size, "tp_hit"
            return None, None

        if bar_high >= stop:
            return (entry - stop) * size, "sl_hit"
        if bar_low <= take_profit:
            return (entry - take_profit) * size, "tp_hit"
        return None, None

    def run(self, df: pd.DataFrame, buy_threshold: float = 0.7, sell_threshold: float = 0.7, dxy: float | None = None, real_yield: float | None = None, sl_multiplier: float = 1.5, rr_ratio: float = 2.0, timeframe: str = "1h"):
        if df is None or df.empty:
            return {
                "trades": 0,
                "total_return": 0.0,
                "win_rate": 0.0,
                "profit": 0.0,
                "final_balance": self.initial_balance,
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "summary": "No data available for backtest.",
            }

        if timeframe in {"5m", "15m"}:
            sl_multiplier = 1.8
            rr_ratio = 1.8

        working = df.copy().reset_index(drop=True)
        if "close" not in working.columns:
            raise ValueError("Backtest data requires a close column.")

        balance = float(self.initial_balance)
        position = None
        trades = []
        trades_detail = []
        equity_curve = [balance]
        peak_balance = balance
        max_drawdown = 0.0

        for idx in range(24, len(working) - 1):
            window = working.iloc[max(0, idx - 24): idx + 1].copy()
            decision, regime, signals = self._evaluate_signal(window, dxy=dxy, real_yield=real_yield)
            direction = decision.get("direction", "wait")
            confidence = float(decision.get("confidence", 0.0))
            current_close = float(working.iloc[idx]["close"])

            if position is None:
                if direction == "buy" and confidence >= buy_threshold:
                    levels = self._calculate_levels(window, "buy", sl_multiplier=sl_multiplier, rr_ratio=rr_ratio)
                    entry = current_close
                    stop = levels["stop"]
                    take_profit = levels["take_profit"]
                    position = {
                        "side": "buy",
                        "entry": entry,
                        "stop": stop,
                        "take_profit": take_profit,
                        "size": 0.5,
                        "opened_at": idx,
                    }
                elif direction == "sell" and confidence >= sell_threshold:
                    levels = self._calculate_levels(window, "sell", sl_multiplier=sl_multiplier, rr_ratio=rr_ratio)
                    entry = current_close
                    stop = levels["stop"]
                    take_profit = levels["take_profit"]
                    position = {
                        "side": "sell",
                        "entry": entry,
                        "stop": stop,
                        "take_profit": take_profit,
                        "size": 0.5,
                        "opened_at": idx,
                    }
                continue

            bar = working.iloc[idx]
            pnl, exit_reason = self._resolve_exit_from_bar(position, bar)

            if pnl is not None:
                balance += pnl
                equity_curve.append(balance)
                peak_balance = max(peak_balance, balance)
                max_drawdown = max(max_drawdown, peak_balance - balance)
                trigger_price = position["stop"] if exit_reason == "sl_hit" else position["take_profit"]
                trade_result = {
                    "side": position["side"],
                    "entry": round(position["entry"], 4),
                    "exit": round(trigger_price, 4),
                    "pnl": round(pnl, 4),
                    "win": pnl > 0,
                    "exit_reason": exit_reason,
                    "opened_at": position["opened_at"],
                    "closed_at": idx,
                    "regime": regime.get("regime", "unknown"),
                    "confidence": round(confidence, 3),
                    "signals": signals,
                }
                trades.append(trade_result)
                trades_detail.append(trade_result)
                position = None

        if not trades:
            return {
                "trades": 0,
                "total_return": 0.0,
                "win_rate": 0.0,
                "profit": 0.0,
                "final_balance": round(balance, 2),
                "best_trade": 0.0,
                "worst_trade": 0.0,
                "expectancy": 0.0,
                "profit_factor": 0.0,
                "max_drawdown": 0.0,
                "trades_detail": [],
                "summary": "No trades triggered during this backtest window.",
            }

        total_profit = balance - self.initial_balance
        win_rate = (sum(1 for trade in trades if trade["win"]) / len(trades)) * 100
        best_trade = max(trade["pnl"] for trade in trades)
        worst_trade = min(trade["pnl"] for trade in trades)
        total_return_pct = (total_profit / self.initial_balance) * 100

        wins = [trade["pnl"] for trade in trades if trade["pnl"] > 0]
        losses = [abs(trade["pnl"]) for trade in trades if trade["pnl"] < 0]
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        expectancy = ((len(wins) / len(trades)) * avg_win) - (((len(losses) / len(trades)) if trades else 0.0) * avg_loss)
        profit_factor = (sum(wins) / sum(losses)) if losses else (float('inf') if wins else 0.0)

        summary = {
            "trades": len(trades),
            "total_return": round(total_return_pct, 2),
            "win_rate": round(win_rate, 2),
            "profit": round(total_profit, 2),
            "final_balance": round(balance, 2),
            "best_trade": round(best_trade, 2),
            "worst_trade": round(worst_trade, 2),
            "expectancy": round(expectancy, 4),
            "profit_factor": round(profit_factor, 4) if isinstance(profit_factor, float) and profit_factor != float('inf') else ('inf' if profit_factor == float('inf') else 0.0),
            "max_drawdown": round(max_drawdown, 4),
            "equity_curve": equity_curve,
            "trades_detail": trades_detail,
            "summary": (
                f"Backtest completed with {len(trades)} trades; "
                f"net return {round(total_return_pct, 2)}%, win rate {round(win_rate, 2)}%, expectancy {round(expectancy, 4)}, profit factor {round(profit_factor, 4) if isinstance(profit_factor, float) and profit_factor != float('inf') else ('inf' if profit_factor == float('inf') else 0.0)}."
            ),
        }
        return summary
