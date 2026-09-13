from __future__ import annotations

from app.data.market_data import fetch_multi_timeframe
from app.strategies.ict_smc import (
    _fvg_zone,
    _mss_bearish_index,
    _mss_bullish_index,
    _retest_confirmed,
    _sweep_high,
    _sweep_low,
)


def _check_retest_in_5m(df_5m, fvg_low, fvg_high, sweep_time):
    if df_5m is None or df_5m.empty:
        return False
    if "timestamp" not in df_5m.columns:
        return False

    future = df_5m[df_5m["timestamp"] >= sweep_time].copy()
    if future.empty:
        return False

    closes = future["close"].astype(float)
    mask = (closes >= float(fvg_low)) & (closes <= float(fvg_high))
    return bool(mask.any())


def scan_unique_ict_events(df_15m, df_5m=None, window_size: int = 30):
    """Return unique sweep -> MSS -> FVG events, deduplicated by sweep index, with retest status when 5m data is available."""
    unique = {}

    for start in range(0, max(1, len(df_15m) - 10)):
        end = min(len(df_15m), start + window_size)
        window = df_15m.iloc[start:end].copy()
        if len(window) < 15:
            continue

        sweep_low, local_idx = _sweep_low(window)
        if sweep_low and local_idx is not None:
            abs_sweep = start + local_idx
            abs_mss = _mss_bullish_index(df_15m, abs_sweep)
            if abs_mss is not None:
                zone = _fvg_zone(df_15m, anchor_index=abs_mss, direction="bullish")
                if zone[0] is not None and zone[1] is not None:
                    key = ("bullish", abs_sweep)
                    if key not in unique:
                        retest = _check_retest_in_5m(df_5m, zone[0], zone[1], df_15m.iloc[abs_sweep]["timestamp"]) if df_5m is not None else False
                        unique[key] = {
                            "kind": "bullish",
                            "sweep_idx": abs_sweep,
                            "mss_idx": abs_mss,
                            "fvg": zone,
                            "timestamp": df_15m.iloc[abs_sweep]["timestamp"],
                            "retest_confirmed": retest,
                        }

        sweep_high, local_idx = _sweep_high(window)
        if sweep_high and local_idx is not None:
            abs_sweep = start + local_idx
            abs_mss = _mss_bearish_index(df_15m, abs_sweep)
            if abs_mss is not None:
                zone = _fvg_zone(df_15m, anchor_index=abs_mss, direction="bearish")
                if zone[0] is not None and zone[1] is not None:
                    key = ("bearish", abs_sweep)
                    if key not in unique:
                        retest = _check_retest_in_5m(df_5m, zone[0], zone[1], df_15m.iloc[abs_sweep]["timestamp"]) if df_5m is not None else False
                        unique[key] = {
                            "kind": "bearish",
                            "sweep_idx": abs_sweep,
                            "mss_idx": abs_mss,
                            "fvg": zone,
                            "timestamp": df_15m.iloc[abs_sweep]["timestamp"],
                            "retest_confirmed": retest,
                        }

    return list(unique.values())


def dump_manual_event_windows(df_15m, df_5m=None, limit: int = 8):
    unique = {}
    for start in range(0, max(1, len(df_15m) - 10)):
        end = min(len(df_15m), start + 30)
        window = df_15m.iloc[start:end].copy()
        if len(window) < 15:
            continue

        sweep_low, local_idx = _sweep_low(window)
        if sweep_low and local_idx is not None:
            abs_sweep = start + local_idx
            abs_mss = _mss_bullish_index(df_15m, abs_sweep)
            if abs_mss is not None:
                zone = _fvg_zone(df_15m, anchor_index=abs_mss, direction="bullish")
                if zone[0] is not None and zone[1] is not None:
                    key = ("bullish", abs_sweep)
                    if key not in unique:
                        unique[key] = {
                            "kind": "bullish",
                            "sweep_idx": abs_sweep,
                            "mss_idx": abs_mss,
                            "fvg": zone,
                            "timestamp": df_15m.iloc[abs_sweep]["timestamp"],
                        }

        sweep_high, local_idx = _sweep_high(window)
        if sweep_high and local_idx is not None:
            abs_sweep = start + local_idx
            abs_mss = _mss_bearish_index(df_15m, abs_sweep)
            if abs_mss is not None:
                zone = _fvg_zone(df_15m, anchor_index=abs_mss, direction="bearish")
                if zone[0] is not None and zone[1] is not None:
                    key = ("bearish", abs_sweep)
                    if key not in unique:
                        unique[key] = {
                            "kind": "bearish",
                            "sweep_idx": abs_sweep,
                            "mss_idx": abs_mss,
                            "fvg": zone,
                            "timestamp": df_15m.iloc[abs_sweep]["timestamp"],
                        }

    for i, evt in enumerate(list(unique.values())[:limit]):
        print(f"\n=== Event: {evt['kind']} sweep_idx={evt['sweep_idx']} mss_idx={evt['mss_idx']} ===")
        print(f"timestamp: {evt['timestamp']}")
        print(f"fvg_zone: {evt['fvg']}")
        window = df_15m.iloc[evt["mss_idx"]:evt["mss_idx"] + 15][["timestamp", "open", "high", "low", "close"]]
        print(window.to_string(index=False))


def main():
    frames = fetch_multi_timeframe(period="30d", base_interval="5m")
    df_15m = frames["15m"].copy()
    df_5m = frames["5m"].copy()

    events = scan_unique_ict_events(df_15m, df_5m=df_5m)
    full_signal = [e for e in events if e["retest_confirmed"]]
    print(f"unique_ict_events={len(events)}")
    print(f"unique_full_signal_events={len(full_signal)}")
    print("sample_full_signals:")
    for event in full_signal[:10]:
        print(event)

    print("\n=== Manual OHLC dump of real event windows ===")
    dump_manual_event_windows(df_15m, df_5m=df_5m, limit=8)


if __name__ == "__main__":
    main()
