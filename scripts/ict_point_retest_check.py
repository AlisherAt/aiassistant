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


frames = fetch_multi_timeframe(period="30d", base_interval="5m")
df15 = frames["15m"].copy()
df5 = frames["5m"].copy()

unique = {}
for start in range(0, max(1, len(df15) - 10)):
    end = min(len(df15), start + 30)
    window = df15.iloc[start:end].copy()
    if len(window) < 15:
        continue

    sweep_low, local_idx = _sweep_low(window)
    if sweep_low and local_idx is not None:
        abs_sweep = start + local_idx
        abs_mss = _mss_bullish_index(df15, abs_sweep)
        if abs_mss is not None:
            zone = _fvg_zone(df15, anchor_index=abs_mss, direction="bullish")
            if zone[0] is not None and zone[1] is not None:
                key = ("bullish", abs_sweep)
                if key not in unique:
                    future = df5[df5["timestamp"] >= df15.iloc[abs_sweep]["timestamp"]].copy()
                    old = bool(((future["close"].astype(float) >= float(zone[0])) & (future["close"].astype(float) <= float(zone[1]))).any())
                    new = _retest_confirmed(future, float(zone[0]), float(zone[1]), "bullish")
                    unique[key] = {
                        "kind": "bullish",
                        "sweep_idx": abs_sweep,
                        "mss_idx": abs_mss,
                        "fvg": zone,
                        "timestamp": df15.iloc[abs_sweep]["timestamp"],
                        "old_retest": old,
                        "new_retest": new,
                    }

    sweep_high, local_idx = _sweep_high(window)
    if sweep_high and local_idx is not None:
        abs_sweep = start + local_idx
        abs_mss = _mss_bearish_index(df15, abs_sweep)
        if abs_mss is not None:
            zone = _fvg_zone(df15, anchor_index=abs_mss, direction="bearish")
            if zone[0] is not None and zone[1] is not None:
                key = ("bearish", abs_sweep)
                if key not in unique:
                    future = df5[df5["timestamp"] >= df15.iloc[abs_sweep]["timestamp"]].copy()
                    old = bool(((future["close"].astype(float) >= float(zone[0])) & (future["close"].astype(float) <= float(zone[1]))).any())
                    new = _retest_confirmed(future, float(zone[0]), float(zone[1]), "bearish")
                    unique[key] = {
                        "kind": "bearish",
                        "sweep_idx": abs_sweep,
                        "mss_idx": abs_mss,
                        "fvg": zone,
                        "timestamp": df15.iloc[abs_sweep]["timestamp"],
                        "old_retest": old,
                        "new_retest": new,
                    }

items = list(unique.values())
print(f"unique_events={len(items)}")
for evt in items[:8]:
    print(
        f"event {evt['kind']} idx={evt['sweep_idx']}: "
        f"old_retest={evt['old_retest']}, new_retest={evt['new_retest']}, "
        f"fvg={evt['fvg']}, timestamp={evt['timestamp']}"
    )
print(f"new_full_signal_events={sum(1 for e in items if e['new_retest'])}")
