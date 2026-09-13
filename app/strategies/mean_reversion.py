"""Mean reversion strategy stub."""


def analyze(df):
    if df is None or df.empty:
        return {"strategy": "mean_reversion", "direction": "neutral", "strength": 0.0, "reason": "No data"}

    close = df["close"].astype(float)
    current = close.iloc[-1]
    mean = close.iloc[-20:].mean()
    deviation = (current - mean) / max(abs(mean), 1.0)

    if deviation < -0.02:
        return {"strategy": "mean_reversion", "direction": "buy", "strength": min(0.9, max(0.4, abs(deviation) * 25.0)), "reason": "Price is below short-term mean"}
    if deviation > 0.02:
        return {"strategy": "mean_reversion", "direction": "sell", "strength": min(0.9, max(0.4, abs(deviation) * 25.0)), "reason": "Price is above short-term mean"}

    return {"strategy": "mean_reversion", "direction": "neutral", "strength": 0.2, "reason": "Price near short-term mean"}
