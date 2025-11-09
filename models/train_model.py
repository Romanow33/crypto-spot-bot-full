import argparse
import pickle
import lightgbm as lgb
from sklearn.model_selection import train_test_split
from models.features import make_features_from_raw, make_X_y
from lightgbm import early_stopping, log_evaluation

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/raw/klines.csv")
    p.add_argument("--out", default="models/model.pkl")
    p.add_argument("--horizon", type=int, default=5, help="Períodos a futuro para predicción")
    p.add_argument("--thresh", type=float, default=0.002, help="Threshold de retorno (0.002 = 0.2%)")
    args = p.parse_args()

    print("Building features...")
    df = make_features_from_raw(args.data)
    print(f"Features shape: {df.shape}")
    
    X, y = make_X_y(df, horizon=args.horizon, ret_thresh=args.thresh)
    print(f"Training samples: {X.shape}")
    print(f"Positive samples: {y.sum()} ({y.mean()*100:.1f}%)")
    
    X_train, X_val, y_train, y_val = train_test_split(
        X, y, test_size=0.2, shuffle=False
    )
    
    dtrain = lgb.Dataset(X_train, label=y_train)
    dval = lgb.Dataset(X_val, label=y_val)
    
    # Parámetros mejorados
    params = {
        "objective": "binary",
        "metric": "auc",
        "learning_rate": 0.05,
        "num_leaves": 31,
        "feature_fraction": 0.8,
        "bagging_fraction": 0.8,
        "bagging_freq": 5,
        "verbosity": -1,
        "max_depth": 6
    }
    
    print("\nTraining model...")
    model = lgb.train(
        params,
        dtrain,
        valid_sets=[dval],
        num_boost_round=500,
        callbacks=[early_stopping(stopping_rounds=30), log_evaluation(20)],
    )
    
    # Feature importance
    print("\nTop 10 feature importance:")
    importance = sorted(zip(X.columns, model.feature_importance()), key=lambda x: -x[1])
    for feat, imp in importance[:10]:
        print(f"  {feat}: {imp}")
    
    with open(args.out, "wb") as f:
        pickle.dump(model, f)
    print(f"\n✅ Saved model to {args.out}")
