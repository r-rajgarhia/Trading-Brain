import sys
import os
import logging
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logger = logging.getLogger(__name__)

def add_indicators(df):
    """Add technical indicators to dataframe"""
    try:
        if df is None or df.empty:
            return None
        
        df = df.copy()
        
        # EMA
        df["ema"] = df["Close"].ewm(span=10, adjust=False).mean()

        # RSI
        delta = df["Close"].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        
        avg_gain = np.mean(gain[-14:]) if len(gain) >= 14 else gain.mean()
        avg_loss = np.mean(loss[-14:]) if len(loss) >= 14 else loss.mean()
        
        rs = avg_gain / avg_loss if avg_loss != 0 else 0
        df["rsi"] = 100 - (100 / (1 + rs)) if rs >= 0 else 100

        # Volatility
        df["return"] = df["Close"].pct_change()
        df["volatility"] = df["return"].rolling(window=10, min_periods=1).std()
        
        df = df.dropna()
        
        if df.empty:
            return None
        
        logger.info(f"Added indicators: {len(df)} rows")
        return df
    except Exception as e:
        logger.error(f"Error adding indicators: {e}")
        return None
