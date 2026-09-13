from __future__ import annotations

from typing import Any

import pandas as pd
import requests
import yfinance as yf

try:
    from fredapi import Fred
except Exception:  # pragma: no cover
    Fred = None


def normalize_ohlcv_columns(df: pd.DataFrame) -> pd.DataFrame:
    normalized = df.copy()

    if isinstance(normalized.columns, pd.MultiIndex):
        normalized.columns = normalized.columns.droplevel(-1)

    normalized.columns = [str(col).lower() for col in normalized.columns]

    if "datetime" in normalized.columns:
        normalized["timestamp"] = pd.to_datetime(normalized["datetime"])
    elif "date" in normalized.columns:
        normalized["timestamp"] = pd.to_datetime(normalized["date"])
    elif "index" in normalized.columns:
        normalized["timestamp"] = pd.to_datetime(normalized["index"])

    return normalized


def _resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    working = df.copy()
    if "timestamp" not in working.columns:
        if isinstance(working.index, pd.DatetimeIndex):
            working = working.reset_index().rename(columns={"index": "timestamp"})
        else:
            working["timestamp"] = pd.to_datetime(working.index)

    working["timestamp"] = pd.to_datetime(working["timestamp"])
    working = working.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)

    if {"open", "high", "low", "close"}.issubset(working.columns):
        result = (
            working.set_index("timestamp")
            .resample(rule)
            .agg({
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
                "volume": "sum",
            })
            .dropna()
            .reset_index()
        )
        if "timestamp" in result.columns:
            result["timestamp"] = pd.to_datetime(result["timestamp"])
        return result

    return working


def fetch_ohlcv(symbol: str, period: str = "60d", interval: str = "15m", auto_adjust: bool = True) -> pd.DataFrame:
    data = yf.download(
        symbol,
        period=period,
        interval=interval,
        auto_adjust=auto_adjust,
        progress=False,
        threads=False,
    )
    if data is None or getattr(data, "empty", True):
        raise ValueError(f"No market data returned for {symbol}")

    df = data.reset_index()
    df = normalize_ohlcv_columns(df)
    return df


def fetch_gold_ohlcv(period: str = "60d", interval: str = "15m") -> pd.DataFrame:
    for symbol in ("GC=F", "XAUUSD=X"):
        try:
            return fetch_ohlcv(symbol, period=period, interval=interval)
        except Exception:
            continue
    raise ValueError("Gold market data unavailable from Yahoo Finance")


def fetch_multi_timeframe(period: str = "180d", base_interval: str = "5m") -> dict[str, pd.DataFrame]:
    base_df = fetch_gold_ohlcv(period=period, interval=base_interval)
    frames = {
        "5m": base_df.copy(),
        "15m": _resample_ohlcv(base_df, "15min"),
        "1h": _resample_ohlcv(base_df, "1h"),
    }
    return {k: v.reset_index(drop=True) for k, v in frames.items() if v is not None and not v.empty}


def fetch_dxy_ohlcv(period: str = "60d", interval: str = "15m") -> pd.DataFrame:
    for symbol in ("DX-Y.NYB", "DX=F"):
        try:
            return fetch_ohlcv(symbol, period=period, interval=interval)
        except Exception:
            continue
    raise ValueError("DXY market data unavailable from Yahoo Finance")


def fetch_dxy() -> float | None:
    try:
        df = fetch_dxy_ohlcv(period="5d", interval="1d")
        if df.empty:
            return None
        close_col = "close" if "close" in df.columns else "adj close"
        return float(df[close_col].dropna().iloc[-1])
    except Exception:
        return None


def fetch_gold_price() -> float | None:
    try:
        df = fetch_gold_ohlcv(period="5d", interval="1d")
        if df.empty:
            return None
        close_col = "close" if "close" in df.columns else "adj close"
        return float(df[close_col].dropna().iloc[-1])
    except Exception:
        return None


def fetch_real_yield(fred_api_key: str | None = None) -> float | None:
    if Fred is not None:
        try:
            fred = Fred(api_key=fred_api_key) if fred_api_key else Fred()
            series = fred.get_series("DFII10", limit=1)
            if not series.empty:
                return float(series.iloc[0])
        except Exception:
            pass

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": "DFII10",
        "api_key": fred_api_key or "",
        "file_type": "json",
        "limit": 1,
        "sort_order": "desc",
    }
    try:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()
        observations = payload.get("observations", [])
        if not observations:
            return None
        latest = observations[0]
        val = latest.get("value")
        return float(val) if val not in (None, ".") else None
    except Exception:
        return None


def fetch_economic_calendar(limit: int = 5) -> list[dict[str, Any]]:
    sample = [
        {"event": "NFP", "impact": "high", "time": "today", "source": "calendar"},
        {"event": "CPI", "impact": "high", "time": "tomorrow", "source": "calendar"},
        {"event": "FOMC", "impact": "high", "time": "this week", "source": "calendar"},
        {"event": "Retail sales", "impact": "medium", "time": "this week", "source": "calendar"},
    ]
    return sample[:limit]
