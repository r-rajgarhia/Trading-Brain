import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import START_CASH, MAX_INVESTMENT_PER_STOCK, EMERGENCY_RESERVE
import logging
logger = logging.getLogger(__name__)

cash = START_CASH
position = 0
entry_price = 0
trade_history = []

def sell_all(price, reason_msg):
    """Handles the actual math of exiting a position"""
    global cash, position, trade_history, entry_price
    
    sale_value = position * price
    pnl = sale_value - (position * entry_price)
    
    cash += sale_value
    units_sold = position
    
    trade_history.append({
        "type": "SELL", 
        "price": price, 
        "units": units_sold, 
        "value": sale_value,
        "reason": reason_msg,
        "pnl": pnl
    })
    
    # Reset for next trade
    position = 0
    entry_price = 0
    return f"SUCCESS: {reason_msg} - Sold for ₹{sale_value:.2f}"

def trade(price, decision):
    global cash, position, trade_history, entry_price
    
    # 1. STEP ONE: Check for Automatic Exits FIRST (if we own stock)
    if position > 0:
        price_change = (price - entry_price) / entry_price
        
        # Stop Loss at 5%
        if price_change <= -0.05:
            return sell_all(price, "STOP LOSS TRIGGERED")
        
        # Take Profit at 10%
        if price_change >= 0.10:
            return sell_all(price, "TAKE PROFIT TRIGGERED")

    # 2. STEP TWO: Your 10% Investment Logic
    investment_amount = START_CASH * MAX_INVESTMENT_PER_STOCK
    reserve_limit = START_CASH * EMERGENCY_RESERVE

    # BUY LOGIC
    if "BUY" in decision.upper():
        if cash - investment_amount >= reserve_limit:
            units_to_buy = investment_amount / price
            entry_price = price # We MUST save this to calculate Stop Loss later
            position += units_to_buy
            cash -= investment_amount
            
            trade_history.append({
                "type": "BUY", 
                "price": price, 
                "units": units_to_buy, 
                "value": investment_amount
            })
            return f"SUCCESS: Bought {units_to_buy:.2f} units"
        else:
            return "REJECTED: Insufficient funds or hitting Emergency Reserve"

    # SELL LOGIC (Triggered by AI)
    elif "SELL" in decision.upper() and position > 0:
        return sell_all(price, "AI SIGNAL SELL")

    return "HOLDING"

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
    
