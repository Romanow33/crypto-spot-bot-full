import pickle
import numpy as np
import pandas as pd

class MLScorer:
    def __init__(self, model_path=None):
        self.model_path = model_path
        self.model = None
        if model_path:
            try:
                with open(model_path, 'rb') as f:
                    self.model = pickle.load(f)
            except Exception as e:
                print('MLScorer: could not load model', e)

    def predict(self, feature_df):
        if self.model is None:
            return np.zeros(len(feature_df))
        
        # Features expandidos (mismo orden que en features.py)
        feature_cols = [
            'ema_diff', 'rsi14', 'ret_1',
            'volatility_5', 'volatility_20',
            'roc_5', 'roc_10',
            'price_to_ema9', 'price_to_ema21', 'price_to_sma50',
            'rsi_change', 'ema_spread_pct',
            'bb_position'
        ]
        
        # Agregar volume_ratio si existe
        if 'volume_ratio' in feature_df.columns:
            feature_cols.append('volume_ratio')
        
        X = feature_df[feature_cols].fillna(0).values
        
        try:
            proba = self.model.predict(X)
            return proba
        except Exception as e:
            print(f"MLScorer predict error: {e}")
            return np.zeros(len(feature_df))
