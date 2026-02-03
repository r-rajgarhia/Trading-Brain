import xgboost as xgb
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging

logger = logging.getLogger(__name__)

def train(df):
    """Train XGBoost model and save"""
    try:
        df["target"] = (df["Close"].shift(-1) > df["Close"]).astype(int)
        X = df[["ema", "rsi", "volatility"]]
        y = df["target"]

        model = xgb.XGBClassifier(n_estimators=50, max_depth=4, random_state=42, verbosity=0)
        model.fit(X, y)

        model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "model.json")
        model.get_booster().save_model(model_path)
        logger.info(f"Model trained and saved")
        return model
    except Exception as e:
        logger.error(f"Error training model: {e}")
        return None
