import streamlit as st
import requests
import pandas as pd
import logging
from typing import Optional, Dict, Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_BASE_URL = "http://localhost:8000"
API_TIMEOUT = 10

st.set_page_config(page_title="Trading Brain", layout="wide", initial_sidebar_state="expanded")

st.markdown("# 📈 Trading Brain", unsafe_allow_html=True)
st.markdown("**AI-Powered Manual Stock Trading Dashboard**", unsafe_allow_html=True)

# ============================================================================
# API Helper Functions
# ============================================================================

def make_api_request(method: str, endpoint: str, data=None, timeout=API_TIMEOUT) -> Optional[Dict[str, Any]]:
    """Make HTTP request to API with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        
        if method == "GET":
            response = requests.get(url, timeout=timeout)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=timeout)
        else:
            return None
        
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to API server. Is it running on http://localhost:8000?")
        return None
    except requests.exceptions.Timeout:
        st.error("⏱️ API request timeout")
        return None
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ API Error: {e.response.json().get('detail', str(e))}")
        return None
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        logger.error(f"API request error: {e}", exc_info=True)
        return None

@st.cache_data(ttl=300)
def get_stocks():
    """Get available stocks"""
    result = make_api_request("GET", "/stocks")
    return result.get("stocks", []) if result else []

def analyze_stock(stock, train_mode=False):
    """Analyze stock"""
    return make_api_request("POST", "/analyze", {"stock": stock, "train_mode": train_mode})

def get_portfolio_stats():
    """Get portfolio stats"""
    return make_api_request("GET", "/portfolio")

def get_trade_history():
    """Get trade history"""
    result = make_api_request("GET", "/trades")
    # Handle both formats: list or dict with 'trades' key
    if isinstance(result, dict) and "trades" in result:
        return result["trades"]
    return result if isinstance(result, list) else []

# ============================================================================
# Main UI
# ============================================================================

# Check API
if make_api_request("GET", "/health") is None:
    st.error("❌ API Server not running. Start with: python api_server.py")
    st.stop()

# Get stocks
all_stocks = get_stocks()
if not all_stocks:
    st.error("Failed to load stocks")
    st.stop()

# Sidebar - Portfolio
with st.sidebar:
    st.markdown("## 💼 Portfolio Summary")
    stats = get_portfolio_stats()
    if stats:
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.metric("💰 Cash", f"₹{stats['cash']:,.0f}")
            st.metric("📊 Position", f"{stats['position']:.2f}")
        with col2:
            pnl_color = "🟢" if stats['total_pnl'] >= 0 else "🔴"
            st.metric("💵 Total Value", f"₹{stats['total_value']:,.0f}")
            st.metric(f"{pnl_color} P&L", f"₹{stats['total_pnl']:,.0f}")
        st.divider()

with st.container():
    st.markdown("### 🔍 Stock Analysis")
    
    col_select, col_train = st.columns([3, 1])
    with col_select:
        stock = st.selectbox("Select Stock", all_stocks, label_visibility="collapsed")
    with col_train:
        train_mode = st.checkbox("🔄 Retrain", value=False, help="Train a new model on latest data")
    
    if st.button("🚀 Analyze & Execute", use_container_width=True, type="primary"):
        with st.spinner("Analyzing..."):
            result = analyze_stock(stock, train_mode=train_mode)
        
        if result:
            # Analysis results in cards
            st.markdown('<div class="analysis-card">', unsafe_allow_html=True)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                signal_emoji = "🟢" if result["signal"] == "BUY" else "🔴"
                st.metric(f"{signal_emoji} Signal", result["signal"])
            with col2:
                st.metric("📊 RSI", f"{result['rsi']:.1f}")
            with col3:
                vol_emoji = "📉" if result['volatility'] < 0.05 else "📈"
                st.metric(f"{vol_emoji} Volatility", f"{result['volatility']:.4f}")
            with col4:
                st.metric("💹 Price", f"₹{result['current_price']:.2f}")
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            # AI Decision
            st.divider()
            st.markdown("### 🤖 AI Decision")
            decision_box = st.container(border=True)
            with decision_box:
                st.write(result["ai_decision"])
            
            # Trade Action
            if "BUY" in result["ai_decision"]:
                st.success(f"✅ **{result['trade_action']}**", icon="✔️")
            elif "SELL" in result["ai_decision"]:
                st.info(f"⚠️ **{result['trade_action']}**")
            else:
                st.warning("⏸️ **HOLD** - No trade signal", icon="⏸️")

# Trade History
st.markdown("---")
st.markdown("### 📋 Trade History")

trades = get_trade_history()
if trades and isinstance(trades, list) and len(trades) > 0:
    df_trades = pd.DataFrame(trades)
    st.dataframe(df_trades, use_container_width=True, hide_index=True)
else:
    st.info("💡 No trades executed yet. Select a stock and click 'Analyze & Execute' to start trading.")

