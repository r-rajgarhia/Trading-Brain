import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import START_CASH
import logging

logger = logging.getLogger(__name__)

# Portfolio state
cash = START_CASH
position = 0
entry_price = 0
trade_history = []

def trade(price, decision):
    """Execute trade based on decision"""
    global cash, position, entry_price, trade_history
    
    try:
        price_val = float(price.iloc[0]) if hasattr(price, 'iloc') else float(price)
    except:
        logger.error("Invalid price")
        return "HOLD"

    # BUY signal
    if "TRADE" in decision and position == 0:
        entry_price = price_val
        position = cash / price_val
        cash = 0.0
        trade_history.append({
            "type": "BUY",
            "price": entry_price,
            "quantity": position,
            "cash_spent": entry_price * position
        })
        logger.info(f"BUY at {entry_price}")
        return "BUY"

    # SELL signal
    if "NO-TRADE" in decision and position > 0:
        exit_price = price_val
        pnl = (exit_price - entry_price) * position
        pnl_pct = ((exit_price - entry_price) / entry_price) * 100
        cash = position * exit_price
        
        trade_history.append({
            "type": "SELL",
            "price": exit_price,
            "quantity": position,
            "cash_received": cash,
            "profit_loss": pnl,
            "profit_loss_pct": pnl_pct
        })
        
        logger.info(f"SELL at {exit_price}, P&L: {pnl:.2f}")
        position = 0.0
        entry_price = 0.0
        return "SELL"

    return "HOLD"

def get_portfolio_stats(current_price=None):
    """Get portfolio statistics"""
    price = float(current_price) if current_price else 0
    pos = float(position) if position != 0 else 0.0
    
    position_value = pos * price if pos > 0 else 0.0
    total_value = cash + position_value
    
    closed_pnl = sum(t.get("profit_loss", 0) for t in trade_history if t["type"] == "SELL")
    unrealized_pnl = (price - entry_price) * pos if pos > 0 and price > 0 else 0.0
    
    return {
        "cash": float(cash),
        "position": pos,
        "position_value": position_value,
        "total_value": total_value,
        "realized_pnl": float(closed_pnl),
        "unrealized_pnl": float(unrealized_pnl),
        "total_pnl": float(closed_pnl + unrealized_pnl),
        "initial_cash": START_CASH,
        "trades_count": len([t for t in trade_history if t["type"] == "BUY"]),
        "closed_trades": len([t for t in trade_history if t["type"] == "SELL"])
    }
