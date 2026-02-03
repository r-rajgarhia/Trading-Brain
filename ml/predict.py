import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xgboost as xgb
import logging

logger = logging.getLogger(__name__)

model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ml", "model.json")
model = None

if os.path.exists(model_path):
    try:
        model = xgb.Booster()
        model.load_model(model_path)
        logger.info("Model loaded")
    except Exception as e:
        logger.error(f"Error loading model: {e}")

def signal(df):
    """Generate trading signal"""
    if model is None:
        logger.warning("Model not available")
        return "BUY"
    
    try:
        X = df[["ema", "rsi", "volatility"]].iloc[-1:]
        dmatrix = xgb.DMatrix(X)
        prob = model.predict(dmatrix)[0]
        print(f"Predicted probability: {prob}")
        return "BUY" if prob > 0.5 else "SELL"
    except Exception as e:
        logger.error(f"Error generating signal: {e}")
        return "BUY"
