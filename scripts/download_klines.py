"""Descarga klines/candles desde Binance y guarda CSV.
Uso:
  python scripts/download_klines.py --symbol BTCUSDT --interval 5m --start 2024-01-01 --out data/raw/btcusdt_5m.csv
"""
import argparse
import time
import requests
import pandas as pd
from datetime import datetime

BASE = 'https://api.binance.com/api/v3/klines'

def iso_to_ms(s):
    dt = datetime.fromisoformat(s)
    return int(dt.timestamp() * 1000)

def download(symbol, interval, start_str, limit=1000):
    start = iso_to_ms(start_str)
    rows = []
    while True:
        params = {
            'symbol': symbol,
            'interval': interval,
            'startTime': start,
            'limit': limit
        }
        r = requests.get(BASE, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if not data:
            break
        rows.extend(data)
        start = data[-1][0] + 1
        if len(data) < limit:
            break
        time.sleep(0.2)
    cols = ['open_time','open','high','low','close','volume','close_time','qav','num_trades','taker_base_vol','taker_quote_vol','ignore']
    df = pd.DataFrame(rows, columns=cols)
    return df

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--symbol', required=True)
    p.add_argument('--interval', default='5m')
    p.add_argument('--start', default='2024-01-01')
    p.add_argument('--out', default='data/raw/klines.csv')
    args = p.parse_args()

    df = download(args.symbol, args.interval, args.start)
    df.to_csv(args.out, index=False)
    print('Saved', args.out, 'rows=', len(df))
