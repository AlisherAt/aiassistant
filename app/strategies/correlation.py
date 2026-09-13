"""Correlation strategy: DXY divergence + gold range breakout."""

import pandas as pd


def analyze(df, dxy=None, real_yield=None):
    if df is None or df.empty:
        return {"strategy": "correlation", "direction": "neutral", "strength": 0.0, "reason": "No market data"}

    if dxy is None and real_yield is None:
        return {"strategy": "correlation", "direction": "neutral", "strength": 0.0, "reason": "No external correlation data"}

    close = pd.to_numeric(df["close"], errors="coerce").dropna()
    if len(close) == 0:
        return {"strategy": "correlation", "direction": "neutral", "strength": 0.0, "reason": "No market data"}

    gold_delta = float(close.iloc[-1] - close.iloc[min(9, len(close)-1)])
    gold_direction = "bullish" if gold_delta > 0 else "bearish" if gold_delta < 0 else "neutral"

    votes = []
    if dxy is not None:
        if dxy < 99.5:
            votes.append(("buy", 0.6, "DXY is weak"))
        elif dxy > 101.5:
            votes.append(("sell", 0.6, "DXY is strong"))
        else:
            votes.append(("neutral", 0.2, "DXY is neutral"))

    if real_yield is not None:
        if real_yield < 2.3:
            votes.append(("buy", 0.7, "Real yield is soft"))
        elif real_yield > 2.6:
            votes.append(("sell", 0.7, "Real yield is elevated"))
        else:
            votes.append(("neutral", 0.2, "Real yield is neutral"))

    buy_total = sum(score for direction, score, _ in votes if direction == "buy")
    sell_total = sum(score for direction, score, _ in votes if direction == "sell")
    neutral_total = sum(score for direction, score, _ in votes if direction == "neutral")

    window = close.iloc[-20:]
    range_low = float(window.min())
    range_high = float(window.max())
    current = float(close.iloc[-1])
    breakout_up = current > range_high * 1.0005
    breakout_down = current < range_low * 0.9995

    dxy_divergence = False
    divergence_reason = "No external correlation imbalance"

    if dxy is not None:
        if dxy < 99.5 and gold_direction == "bearish":
            dxy_divergence = True
            divergence_reason = "DXY is weak while gold remains soft; bullish divergence"
        elif dxy > 101.5 and gold_direction == "bullish":
            dxy_divergence = True
            divergence_reason = "DXY is strong while gold stays firm; bearish divergence"

    if real_yield is not None:
        if real_yield < 2.3 and gold_direction == "bearish":
            dxy_divergence = True
            divergence_reason = "Real yield is soft and gold is not yet responding"
        elif real_yield > 2.6 and gold_direction == "bullish":
            dxy_divergence = True
            divergence_reason = "Real yield is elevated and gold is not yet correcting lower"

    if dxy_divergence and breakout_up:
        return {"strategy": "correlation", "direction": "buy", "strength": 0.8, "reason": f"{divergence_reason}; range breakout confirms bullish continuation"}
    if dxy_divergence and breakout_down:
        return {"strategy": "correlation", "direction": "sell", "strength": 0.8, "reason": f"{divergence_reason}; range breakdown confirms bearish continuation"}
    if dxy_divergence:
        return {"strategy": "correlation", "direction": "neutral", "strength": 0.4, "reason": "DXY divergence detected, waiting for range breakout"}

    if buy_total > sell_total and buy_total >= neutral_total:
        if breakout_up:
            return {"strategy": "correlation", "direction": "buy", "strength": 0.8, "reason": "Macro support and gold breakout confirm bullish continuation"}
        return {"strategy": "correlation", "direction": "buy", "strength": 0.68, "reason": "Macro backdrop supports gold even before a fresh breakout"}
    if sell_total > buy_total and sell_total >= neutral_total:
        if breakout_down:
            return {"strategy": "correlation", "direction": "sell", "strength": 0.8, "reason": "Macro headwind and gold breakdown confirm bearish continuation"}
        return {"strategy": "correlation", "direction": "sell", "strength": 0.68, "reason": "Macro backdrop is bearish even before a fresh breakdown"}
