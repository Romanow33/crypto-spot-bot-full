from binance.spot import Spot as BinanceClient
import pandas as pd
import os
from datetime import datetime

MODE = os.getenv("MODE", "dev")
API_SECRET = (
    os.getenv("BINANCE_API_SECRET_DEV")
    if MODE == "dev"
    else os.getenv("BINANCE_API_SECRET")
)
API_KEY = (
    os.getenv("BINANCE_API_KEY_DEV") if MODE == "dev" else os.getenv("BINANCE_API_KEY")
)
TESTNET_URL = "https://testnet.binance.vision"

if MODE == "dev":
    client = BinanceClient(API_KEY, API_SECRET, base_url=TESTNET_URL)
else:
    client = BinanceClient(API_KEY, API_SECRET)


def get_latest_klines(symbol="BTCUSDT", interval="5m", limit=500):
    # Llamar al método correcto
    response = client.klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(
        response,
        columns=[
            "open_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
            "close_time",
            "quote_asset_volume",
            "num_trades",
            "taker_buy_base",
            "taker_buy_quote",
            "ignore",
        ],
    )
    # convertir columnas numéricas
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = df[col].astype(float)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    return df
