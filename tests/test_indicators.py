import pandas as pd
from bot.strategy import compute_features

def test_compute_features():
    df = pd.DataFrame({'close':[100,101,102,103,102,101,100,99,98,97,96,95,96,97,98,99,100,101,102,103]})
    out = compute_features(df)
    assert 'ema9' in out.columns
    assert 'rsi14' in out.columns
