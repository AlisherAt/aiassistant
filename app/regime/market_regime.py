"""Market regime detection based on ADX, volatility, and news windows."""

import numpy as np


def _compute_adx(df, period=14):
    close = df["close"].astype(float)
    if len(close) < period + 5:
        return 22.0

    returns = close.pct_change().fillna(0)
    up = returns.where(returns > 0, 0)
    atr = np.std(returns.to_numpy()) * 100
    if np.isnan(atr):
        atr = 0.0
    return max(10.0, min(70.0, atr * 2.5 + np.mean(up) * 1000))


def classify_market_regime(df, economic_event=None):
    close = df["close"].astype(float)
    adx = _compute_adx(df)
    volatility = float(np.std(close.pct_change().dropna().to_numpy()) * 100) if len(close) > 1 else 0.0
    recent_trend = (close.iloc[-1] - close.iloc[0]) / max(abs(close.iloc[0]), 1.0)

    if economic_event and economic_event.get("is_high_impact"):
        regime = "news_window"
        trend_direction = "neutral"
    elif recent_trend > 0.05 or (adx > 25 and recent_trend >= 0):
        regime = "trending"
        trend_direction = "bullish"
    elif recent_trend < -0.05 or (adx > 25 and recent_trend < 0):
        regime = "trending"
        trend_direction = "bearish"
    elif volatility < 0.3:
        regime = "ranging"
        trend_direction = "neutral"
    else:
        regime = "ranging"
        trend_direction = "neutral"

    raw_weights = {
        "trend_following": 0.40 if regime in {"trending", "trending_bullish", "trending_bearish"} else 0.15,
        "ict_smc": 0.35 if regime != "ranging" else 0.20,
        "correlation": 0.25 if regime in {"trending", "trending_bullish", "trending_bearish", "news_window"} else 0.20,
    }
    total_weight = sum(raw_weights.values())
    weights = {key: round(value / total_weight, 4) for key, value in raw_weights.items()}

    return {
        "regime": regime,
        "trend_direction": trend_direction,
        "adx": round(adx, 2),
        "volatility": round(volatility, 4),
        "recent_trend": round(recent_trend, 4),
        "weights": weights,
    }
