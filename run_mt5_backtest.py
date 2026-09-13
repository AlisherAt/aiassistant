from datetime import datetime, timedelta
import pandas as pd
import MetaTrader5 as mt5

from app.backtest.engine import BacktestEngine
from app.config import settings
from app.data.market_data import fetch_dxy, fetch_real_yield


login = int(settings.mt5_login)
password = settings.mt5_password
server = settings.mt5_server
print('INIT', mt5.initialize(login=login, password=password, server=server))

df = None
for sym in ['XAUUSD', 'GOLD', 'XAUUSDm', 'XAUUSD_i']:
    try:
        ok = mt5.symbol_select(sym, True)
        print('symbol_select', sym, ok, 'last_error', mt5.last_error())
        if ok:
            rates = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M5, datetime.now() - timedelta(days=180), datetime.now())
            print('rates_len', None if rates is None else len(rates), 'sym', sym)
            if rates is not None and len(rates) > 0:
                df = pd.DataFrame(rates)
                df['time'] = pd.to_datetime(df['time'], unit='s')
                df = df.rename(columns={'time': 'timestamp'})
                break
    except Exception as exc:
        print('ERR', sym, type(exc).__name__, exc)
        continue

mt5.shutdown()
if df is None:
    raise RuntimeError('No MT5 data available')

summary = BacktestEngine(initial_balance=10000).run(
    df,
    buy_threshold=0.7,
    sell_threshold=0.7,
    dxy=fetch_dxy(),
    real_yield=fetch_real_yield(settings.fred_api_key),
    timeframe='5m',
)

print('SUMMARY_START')
for key in ['trades', 'total_return', 'win_rate', 'profit', 'final_balance', 'best_trade', 'worst_trade', 'expectancy', 'profit_factor', 'max_drawdown']:
    print(f'{key}={summary.get(key)}')
print('TRADES_DETAIL', summary.get('trades_detail'))
print('SUMMARY_END')
