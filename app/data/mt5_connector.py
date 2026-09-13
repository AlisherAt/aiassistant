from __future__ import annotations

import pandas as pd

try:
    import MetaTrader5 as mt5
except Exception:  # pragma: no cover
    mt5 = None


class MT5Connector:
    def __init__(self, login: str | None = None, password: str | None = None, server: str | None = None):
        self.login = login
        self.password = password
        self.server = server
        self.connected = False

    def connect(self) -> bool:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not installed")
        if not self.login or not self.password or not self.server:
            raise RuntimeError("MT5 credentials are missing; set MT5_LOGIN, MT5_PASSWORD and MT5_SERVER")
        if not mt5.initialize(login=int(self.login), password=self.password, server=self.server):
            raise RuntimeError(f"MT5 initialize failed: {mt5.last_error()}")
        self.connected = True
        return True

    def get_bars(self, symbol: str, timeframe: int, count: int = 200) -> pd.DataFrame:
        if mt5 is None:
            raise RuntimeError("MetaTrader5 package is not installed")
        if not self.connected:
            self.connect()

        if not mt5.symbol_select(symbol, True):
            raise ValueError(f"Symbol {symbol} is not available in the MT5 terminal")

        rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, count)
        if rates is None or len(rates) == 0:
            raise ValueError(f"No bars returned for {symbol}")

        df = pd.DataFrame(rates)
        df["time"] = pd.to_datetime(df["time"], unit="s")
        df = df.rename(columns={"time": "timestamp"})
        return df

    def disconnect(self):
        if mt5 is not None and self.connected:
            mt5.shutdown()
        self.connected = False


def fetch_live_gold_from_mt5(login: str | None, password: str | None, server: str | None) -> pd.DataFrame | None:
    if not login or not password or not server:
        return None

    connector = MT5Connector(login=login, password=password, server=server)
    try:
        connector.connect()
        for symbol in ("XAUUSD", "GOLD", "XAUUSDm", "XAUUSD_i"):
            try:
                return connector.get_bars(symbol, mt5.TIMEFRAME_M15, count=200)
            except Exception:
                continue
        return None
    except Exception:
        return None
    finally:
        connector.disconnect()
