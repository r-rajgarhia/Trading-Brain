"""
FastAPI Backend Server for GenAI Trading Brain
Handles all trading operations and provides HTTP API endpoints
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
import logging
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.universe import NIFTY50
from data.downloader import fetch
from features.indicators import add_indicators
from ml.train import train
from ml.predict import signal
from brain.genai import ask_llm
from execution.paper_trader import trade, get_portfolio_stats, trade_history
from utils import is_market_hours, is_weekday

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="GenAI Trading Brain API",
    description="API for manual AI-driven trading",
    version="1.0.0"
)

# Pydantic models for request/response
class TradeRequest(BaseModel):
    stock: str
    train_mode: Optional[bool] = False

# ============================================================================
# Health & Status Endpoints
# ============================================================================

@app.get("/", tags=["Health"])
async def root():
    """API root endpoint"""
    return {
        "name": "GenAI Trading Brain API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health", tags=["Health"])
async def health_check():
    """Check API health and market status"""
    try:
        return {
            "status": "healthy",
            "market_hours": is_market_hours() and is_weekday()
        }
    except Exception as e:
        logger.error(f"Health check error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Stock & Portfolio Endpoints
# ============================================================================

@app.get("/stocks", tags=["Stocks"])
async def get_stocks():
    """Get list of available stocks (NIFTY-50)"""
    try:
        return {"stocks": NIFTY50}
    except Exception as e:
        logger.error(f"Error fetching stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/portfolio", tags=["Portfolio"])
async def get_portfolio(current_price: Optional[float] = None):
    """Get current portfolio statistics"""
    try:
        return get_portfolio_stats(current_price)
    except Exception as e:
        logger.error(f"Error getting portfolio stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/trades", tags=["Portfolio"])
async def get_trades():
    """Get trade history"""
    try:
        return trade_history
    except Exception as e:
        logger.error(f"Error fetching trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Manual Trading Endpoints
# ============================================================================

@app.post("/analyze", tags=["Manual Trading"])
async def analyze_stock(request: TradeRequest):
    """Analyze a single stock and return trading decision"""
    try:
        stock = request.stock
        logger.info(f"Analyzing stock: {stock}")
        
        # Fetch data
        df = fetch(stock)
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail=f"No data available for {stock}")
        
        # Add indicators
        df = add_indicators(df)
        if df is None or df.empty:
            raise HTTPException(status_code=400, detail=f"Failed to add indicators for {stock}")
        
        # Train model only if requested
        if request.train_mode:
            train(df)
            logger.info(f"Model trained for {stock}")
        else:
            logger.info(f"Using saved model for {stock}")
        #print(df.head())
        # Get signal
        sig = signal(df)
        last = df.iloc[-1]

        
        # Get AI decision
        ai_decision = ask_llm(sig, last["rsi"], last["volatility"])
        
        # Execute trade
        trade_action = trade(last["Close"], ai_decision)
        
        return {
            "stock": stock,
            "signal": sig,
            "rsi": float(last["rsi"].iloc[0]) if hasattr(last["rsi"], 'iloc') else float(last["rsi"]),
            "volatility": float(last["volatility"].iloc[0]) if hasattr(last["volatility"], 'iloc') else float(last["volatility"]),
            "current_price": float(last["Close"].iloc[0]) if hasattr(last["Close"], 'iloc') else float(last["Close"]),
            "ai_decision": ai_decision,
            "trade_action": trade_action,
            "train_mode": request.train_mode
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing stock {request.stock}: {e}")
        raise HTTPException(status_code=500, detail=str(e))



if __name__ == "__main__":
    import uvicorn
    logger.info("Starting FastAPI server on http://0.0.0.0:8000")
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
