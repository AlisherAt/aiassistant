"""ICT/SMC-inspired strategy: sweep + MSS + FVG retest."""

import pandas as pd


def _sweep_low(df: pd.DataFrame) -> tuple[bool, int | None]:
    if df is None or df.empty or len(df) < 15:
        return False, None

    start = max(0, len(df) - 20)
    for idx in range(start, len(df) - 1):
        window = df.iloc[max(0, idx - 10):idx]
        if window.empty:
            continue
        prior_low = float(window["low"].min())
        current_low = float(df.iloc[idx]["low"])
        current_close = float(df.iloc[idx]["close"])
        if current_low < prior_low and current_close > prior_low:
            return True, idx
    return False, None


def _sweep_high(df: pd.DataFrame) -> tuple[bool, int | None]:
    if df is None or df.empty or len(df) < 15:
        return False, None

    start = max(0, len(df) - 20)
    for idx in range(start, len(df) - 1):
        window = df.iloc[max(0, idx - 10):idx]
        if window.empty:
            continue
        prior_high = float(window["high"].max())
        current_high = float(df.iloc[idx]["high"])
        current_close = float(df.iloc[idx]["close"])
        if current_high > prior_high and current_close < prior_high:
            return True, idx
    return False, None


def _mss_bullish(df: pd.DataFrame, sweep_index: int) -> bool:
    if df is None or df.empty or sweep_index is None:
        return False
    if sweep_index < 0 or len(df) <= sweep_index + 1:
        return False

    post_window = df.iloc[sweep_index + 1:sweep_index + 4]
    if post_window.empty:
        return False

    pre_window = df.iloc[max(0, sweep_index - 3):sweep_index]
    reference_high = float(pre_window["high"].max()) if not pre_window.empty else float(df.iloc[sweep_index]["high"])
    return float(post_window["high"].max()) > reference_high


def _mss_bullish_index(df: pd.DataFrame, sweep_index: int) -> int | None:
    if df is None or df.empty or sweep_index is None:
        return None
    if sweep_index < 0 or len(df) <= sweep_index + 1:
        return None

    max_scan = min(len(df) - 1, sweep_index + 6)
    for idx in range(sweep_index + 1, max_scan + 1):
        pre_window = df.iloc[max(0, idx - 3):idx]
        if pre_window.empty:
            continue
        reference_high = float(pre_window["high"].max())
        if float(df.iloc[idx]["high"]) > reference_high:
            return idx
    return None


def _mss_bearish(df: pd.DataFrame, sweep_index: int) -> bool:
    if df is None or df.empty or sweep_index is None:
        return False
    if sweep_index < 0 or len(df) <= sweep_index + 1:
        return False

    post_window = df.iloc[sweep_index + 1:sweep_index + 4]
    if post_window.empty:
        return False

    pre_window = df.iloc[max(0, sweep_index - 3):sweep_index]
    reference_low = float(pre_window["low"].min()) if not pre_window.empty else float(df.iloc[sweep_index]["low"])
    return float(post_window["low"].min()) < reference_low


def _mss_bearish_index(df: pd.DataFrame, sweep_index: int) -> int | None:
    if df is None or df.empty or sweep_index is None:
        return None
    if sweep_index < 0 or len(df) <= sweep_index + 1:
        return None

    max_scan = min(len(df) - 1, sweep_index + 6)
    for idx in range(sweep_index + 1, max_scan + 1):
        pre_window = df.iloc[max(0, idx - 3):idx]
        if pre_window.empty:
            continue
        reference_low = float(pre_window["low"].min())
        if float(df.iloc[idx]["low"]) < reference_low:
            return idx
    return None


def _fvg_zone(df: pd.DataFrame, anchor_index: int | None = None, direction: str = "bullish") -> tuple[float | None, float | None]:
    if df is None or df.empty or len(df) < 3:
        return None, None

    if anchor_index is None:
        anchor_index = len(df) - 3

    start = max(0, anchor_index - 2)
    end = min(len(df) - 3, anchor_index + 2)
    for i in range(start, end + 1):
        a, b, c = df.iloc[i], df.iloc[i + 1], df.iloc[i + 2]
        if direction == "bullish":
            if float(c["low"]) > float(a["high"]) and float(c["close"]) > float(b["close"]):
                return float(a["high"]), float(c["low"])
        else:
            if float(c["high"]) < float(a["low"]) and float(c["close"]) < float(b["close"]):
                return float(c["high"]), float(a["low"])
    return None, None


def _retest_confirmed(df_5m: pd.DataFrame, fvg_low: float, fvg_high: float, direction: str, max_bars: int = 20) -> bool:
    """Retest requires a touch of the FVG and a directional close after the touch, without a full opposite-side break-through."""
    if df_5m is None or df_5m.empty or len(df_5m) < 2:
        return False

    window = df_5m.tail(max_bars).reset_index(drop=True)
    for i in range(len(window) - 1):
        candle = window.iloc[i]
        next_candle = window.iloc[i + 1]
        touched = float(candle["low"]) <= fvg_high and float(candle["high"]) >= fvg_low
        if not touched:
            continue

        if direction == "bullish":
            broke_through_down = float(next_candle["close"]) < fvg_low * 0.998
            rejected_up = float(next_candle["close"]) > float(candle["close"]) and float(next_candle["close"]) >= fvg_low
            if rejected_up and not broke_through_down:
                return True
        else:
            broke_through_up = float(next_candle["close"]) > fvg_high * 1.002
            rejected_down = float(next_candle["close"]) < float(candle["close"]) and float(next_candle["close"]) <= fvg_high
            if rejected_down and not broke_through_up:
                return True

    return False


def analyze(df_15m=None, df_5m=None, debug=False):
    stages = {
        "sweep_detected": False,
        "sweep_direction": None,
        "mss_confirmed": False,
        "fvg_found": False,
        "retest_confirmed": False,
    }

    if df_15m is None or df_15m.empty:
        result = {"strategy": "ict_smc", "direction": "neutral", "strength": 0.0, "reason": "No 15m structure data"}
        return (result, stages) if debug else result

    sweep_low, sweep_index = _sweep_low(df_15m)
    sweep_high, sweep_index_high = _sweep_high(df_15m)

    if sweep_low or sweep_high:
        stages["sweep_detected"] = True
        stages["sweep_direction"] = "bullish" if sweep_low else "bearish"

    if sweep_low:
        mss_index = _mss_bullish_index(df_15m, sweep_index)
        if mss_index is not None:
            stages["mss_confirmed"] = True
            fvg_low, fvg_high = _fvg_zone(df_15m, anchor_index=mss_index, direction="bullish")
            if fvg_low is not None and fvg_high is not None:
                stages["fvg_found"] = True
                if df_5m is not None and not df_5m.empty:
                    if _retest_confirmed(df_5m, float(fvg_low), float(fvg_high), "bullish"):
                        stages["retest_confirmed"] = True
                        result = {"strategy": "ict_smc", "direction": "buy", "strength": 0.8, "reason": "Liquidity sweep + MSS bullish + FVG retest"}
                        return (result, stages) if debug else result
                result = {"strategy": "ict_smc", "direction": "buy", "strength": 0.7, "reason": "Liquidity sweep + MSS bullish, pending FVG retest"}
                return (result, stages) if debug else result
            result = {"strategy": "ict_smc", "direction": "neutral", "strength": 0.3, "reason": "Sweep found, MSS confirmed, but FVG absent"}
            return (result, stages) if debug else result

    if sweep_high:
        mss_index = _mss_bearish_index(df_15m, sweep_index_high)
        if mss_index is not None:
            stages["mss_confirmed"] = True
            fvg_low, fvg_high = _fvg_zone(df_15m, anchor_index=mss_index, direction="bearish")
            if fvg_low is not None and fvg_high is not None:
                stages["fvg_found"] = True
                if df_5m is not None and not df_5m.empty:
                    if _retest_confirmed(df_5m, float(fvg_low), float(fvg_high), "bearish"):
                        stages["retest_confirmed"] = True
                        result = {"strategy": "ict_smc", "direction": "sell", "strength": 0.8, "reason": "Liquidity sweep + MSS bearish + FVG retest"}
                        return (result, stages) if debug else result
                result = {"strategy": "ict_smc", "direction": "sell", "strength": 0.7, "reason": "Liquidity sweep + MSS bearish, pending FVG retest"}
                return (result, stages) if debug else result
            result = {"strategy": "ict_smc", "direction": "neutral", "strength": 0.3, "reason": "Sweep found, MSS confirmed, but FVG absent"}
            return (result, stages) if debug else result

    if sweep_low or sweep_high:
        result = {"strategy": "ict_smc", "direction": "neutral", "strength": 0.3, "reason": "Sweep without MSS confirmation"}
        return (result, stages) if debug else result

    result = {"strategy": "ict_smc", "direction": "neutral", "strength": 0.15, "reason": "No valid sweep + MSS + FVG setup"}
    return (result, stages) if debug else result
