"""Trend-following strategy with HTF bias + 15m zone + 5m confirmation."""

import pandas as pd


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.astype(float).ewm(span=span, adjust=False).mean()


def _bullish_engulfing(last: pd.Series, prev: pd.Series) -> bool:
    body_current = abs(float(last.get("close", 0.0)) - float(last.get("open", 0.0)))
    body_prev = abs(float(prev.get("close", 0.0)) - float(prev.get("open", 0.0)))
    return (
        float(last.get("close", 0.0)) > float(last.get("open", 0.0))
        and float(last.get("close", 0.0)) > float(prev.get("high", 0.0))
        and float(last.get("open", 0.0)) < float(prev.get("close", 0.0))
        and body_current >= 0.5 * max(body_prev, 1e-9)
    )


def _bearish_engulfing(last: pd.Series, prev: pd.Series) -> bool:
    body_current = abs(float(last.get("close", 0.0)) - float(last.get("open", 0.0)))
    body_prev = abs(float(prev.get("close", 0.0)) - float(prev.get("open", 0.0)))
    return (
        float(last.get("close", 0.0)) < float(last.get("open", 0.0))
        and float(last.get("close", 0.0)) < float(prev.get("low", 0.0))
        and float(last.get("open", 0.0)) > float(prev.get("close", 0.0))
        and body_current >= 0.5 * max(body_prev, 1e-9)
    )


def analyze(df_1h=None, df_15m=None, df_5m=None):
    if df_1h is None or df_1h.empty:
        return {"strategy": "trend_following", "direction": "neutral", "strength": 0.0, "reason": "No HTF trend data"}

    close_1h = pd.to_numeric(df_1h["close"], errors="coerce").dropna()
    if len(close_1h) < 2:
        return {"strategy": "trend_following", "direction": "neutral", "strength": 0.1, "reason": "Not enough HTF history"}

    # Bootstrap fix: compute EMA on the available history instead of requiring a full
    # 200-bar window. Short rolling windows are common in backtests, and EWMA still
    # provides a valid directional bias on the data available at that point in time.
    ema50 = _ema(close_1h, 50).iloc[-1]
    ema200 = _ema(close_1h, 200).iloc[-1]
    last_close = float(close_1h.iloc[-1])

    if last_close > ema50 and ema50 > ema200:
        bias = "bullish"
    elif last_close < ema50 and ema50 < ema200:
        bias = "bearish"
    else:
        return {"strategy": "trend_following", "direction": "neutral", "strength": 0.0, "reason": "No clear HTF bias"}

    if df_15m is None or df_15m.empty:
        return {"strategy": "trend_following", "direction": "neutral", "strength": 0.25, "reason": "No 15m zone data"}

    close_15m = pd.to_numeric(df_15m["close"], errors="coerce").dropna()
    ema20_15m = _ema(close_15m, 20).iloc[-1]
    current_15m = float(close_15m.iloc[-1])

    if bias == "bullish":
        zone_ok = current_15m <= ema20_15m * 1.001
    else:
        zone_ok = current_15m >= ema20_15m * 0.999

    if not zone_ok:
        return {"strategy": "trend_following", "direction": "neutral", "strength": 0.2, "reason": "Price not in pullback zone"}

    if df_5m is None or df_5m.empty:
        return {"strategy": "trend_following", "direction": "neutral", "strength": 0.4, "reason": "In zone, waiting for confirmation"}

    bars_5m = df_5m.dropna(subset=["open", "high", "low", "close"]).copy()
    if len(bars_5m) < 2:
        return {"strategy": "trend_following", "direction": "neutral", "strength": 0.4, "reason": "In zone, waiting for confirmation"}

    last_bar = bars_5m.iloc[-1]
    prev_bar = bars_5m.iloc[-2]

    bullish_confirm = (
        bias == "bullish"
        and (
            _bullish_engulfing(last_bar, prev_bar)
            or float(last_bar.get("close", 0.0)) > float(prev_bar.get("high", 0.0))
        )
    )
    bearish_confirm = (
        bias == "bearish"
        and (
            _bearish_engulfing(last_bar, prev_bar)
            or float(last_bar.get("close", 0.0)) < float(prev_bar.get("low", 0.0))
        )
    )

    if bullish_confirm:
        strength = 0.82 if _bullish_engulfing(last_bar, prev_bar) else 0.75
        return {"strategy": "trend_following", "direction": "buy", "strength": min(0.9, strength), "reason": "HTF bullish bias + pullback zone + 5m confirmation"}

    if bearish_confirm:
        strength = 0.82 if _bearish_engulfing(last_bar, prev_bar) else 0.75
        return {"strategy": "trend_following", "direction": "sell", "strength": min(0.9, strength), "reason": "HTF bearish bias + pullback zone + 5m confirmation"}

    return {"strategy": "trend_following", "direction": "neutral", "strength": 0.4, "reason": "In zone, waiting for confirmation"}
