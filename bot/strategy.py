import numpy as np
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

def ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def sma(series, period):
    return series.rolling(window=period).mean()

def rsi(series, period=14):
    delta = series.diff()
    up = delta.clip(lower=0)
    down = -1 * delta.clip(upper=0)
    ma_up = up.ewm(alpha=1/period, adjust=False).mean()
    ma_down = down.ewm(alpha=1/period, adjust=False).mean()
    rs = ma_up / (ma_down + 1e-9)
    return 100 - (100 / (1 + rs))

def compute_features(df: pd.DataFrame):
    df = df.copy()
    df['close'] = df['close'].astype(float)
    
    # RSI(2) para mean reversion
    df['rsi2'] = rsi(df['close'], 2)
    
    # Moving averages para contexto
    df['sma50'] = sma(df['close'], 50)
    df['sma200'] = sma(df['close'], 200)
    
    # Volatilidad para dimensionar posiciones
    df['atr14'] = df['close'].rolling(14).std() * 1.5
    
    # Features adicionales para ML
    df['ema9'] = ema(df['close'], 9)
    df['ema21'] = ema(df['close'], 21)
    df['rsi14'] = rsi(df['close'], 14)
    df['ema_diff'] = df['ema9'] - df['ema21']
    df['ret_1'] = df['close'].pct_change(1)
    df['volatility_5'] = df['close'].rolling(5).std()
    df['volatility_20'] = df['close'].rolling(20).std()
    df['roc_5'] = df['close'].pct_change(5)
    df['roc_10'] = df['close'].pct_change(10)
    df['price_to_ema9'] = (df['close'] - df['ema9']) / df['ema9']
    df['price_to_ema21'] = (df['close'] - df['ema21']) / df['ema21']
    df['price_to_sma50'] = (df['close'] - df['sma50']) / df['sma50']
    df['rsi_change'] = df['rsi14'].diff()
    df['ema_spread_pct'] = (df['ema9'] - df['ema21']) / df['ema21']
    df['bb_upper'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
    df['bb_lower'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-9)
    
    if 'volume' in df.columns:
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_ma5'] + 1e-9)
    
    df = df.dropna().reset_index(drop=True)
    return df

def rule_signal(row):
    """RSI(2) Mean Reversion Strategy
    
    BUY: RSI(2) < 10 (extreme oversold)
    SELL: RSI(2) > 90 (extreme overbought)
    
    Filters:
    - Trend: Only buy if price > SMA200 (long-term uptrend)
    - ML: Optional ML filter
    """
    use_trend_filter = os.getenv("USE_TREND_FILTER", "true").lower() == "true"
    use_ml_filter = os.getenv("USE_ML_FILTER", "false").lower() == "true"
    ml_threshold = float(os.getenv("ML_THRESHOLD", "0.5"))
    
    rsi2_buy_level = float(os.getenv("RSI2_BUY_LEVEL", "10"))
    rsi2_sell_level = float(os.getenv("RSI2_SELL_LEVEL", "90"))
    
    # BUY: RSI(2) oversold
    if row['rsi2'] < rsi2_buy_level:
        # Trend filter: only buy in long-term uptrend
        if use_trend_filter and row['close'] <= row['sma200']:
            return 0
        
        # ML filter
        if use_ml_filter and row['ml_score'] < ml_threshold:
            return 0
        
        return 1
    
    # SELL: RSI(2) overbought
    if row['rsi2'] > rsi2_sell_level:
        return -1
    
    return 0

def build_signals(df, ml_scores=None, ml_thresh=0.5):
    df2 = compute_features(df)
    
    if ml_scores is not None and len(ml_scores) == len(df2):
        df2['ml_score'] = ml_scores
    else:
        df2['ml_score'] = 0.0
    
    df2['rule'] = df2.apply(rule_signal, axis=1)
    df2['final'] = df2['rule']
    
    return df2
