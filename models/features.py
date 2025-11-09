import pandas as pd
from bot.strategy import compute_features

def make_features_from_raw(raw_csv, out_csv=None):
    df = pd.read_csv(raw_csv)
    df2 = compute_features(df)
    
    # Agregar features adicionales
    df2 = add_advanced_features(df2)
    
    if out_csv:
        df2.to_csv(out_csv, index=False)
    return df2

def add_advanced_features(df):
    """Agregar features avanzados para ML"""
    df = df.copy()
    
    # Volatilidad
    df['volatility_5'] = df['close'].rolling(5).std()
    df['volatility_20'] = df['close'].rolling(20).std()
    
    # Momentum
    df['roc_5'] = df['close'].pct_change(5)
    df['roc_10'] = df['close'].pct_change(10)
    
    # Price position relative to moving averages
    df['price_to_ema9'] = (df['close'] - df['ema9']) / df['ema9']
    df['price_to_ema21'] = (df['close'] - df['ema21']) / df['ema21']
    df['price_to_sma50'] = (df['close'] - df['sma50']) / df['sma50']
    
    # RSI momentum
    df['rsi_change'] = df['rsi14'].diff()
    
    # Volume features
    if 'volume' in df.columns:
        df['volume_ma5'] = df['volume'].rolling(5).mean()
        df['volume_ratio'] = df['volume'] / (df['volume_ma5'] + 1e-9)
    
    # EMA spread
    df['ema_spread_pct'] = (df['ema9'] - df['ema21']) / df['ema21']
    
    # Bollinger-style bands
    df['bb_upper'] = df['close'].rolling(20).mean() + 2 * df['close'].rolling(20).std()
    df['bb_lower'] = df['close'].rolling(20).mean() - 2 * df['close'].rolling(20).std()
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'] + 1e-9)
    
    return df.fillna(0)

def make_X_y(df, horizon=3, ret_thresh=0.001):
    df = df.copy().reset_index(drop=True)
    df['future'] = df['close'].shift(-horizon).astype(float)
    df['future_ret'] = (df['future'] - df['close'].astype(float)) / df['close'].astype(float)
    df['y'] = (df['future_ret'] > ret_thresh).astype(int)
    
    # Features expandidos
    feature_cols = [
        'ema_diff', 'rsi14', 'ret_1',
        'volatility_5', 'volatility_20',
        'roc_5', 'roc_10',
        'price_to_ema9', 'price_to_ema21', 'price_to_sma50',
        'rsi_change', 'ema_spread_pct',
        'bb_position'
    ]
    
    # Agregar volume si existe
    if 'volume_ratio' in df.columns:
        feature_cols.append('volume_ratio')
    
    X = df[feature_cols].fillna(0)
    y = df['y'].fillna(0).astype(int)
    valid = ~df['future'].isna()
    
    return X[valid], y[valid]
