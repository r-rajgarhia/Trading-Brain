import os
import logging
import hashlib
import time
from functools import lru_cache
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache for API responses (avoid repeated calls)
response_cache = {}
CACHE_TTL = 3600  # 1 hour cache

# Rate limiting & quota management
last_api_call = None
MIN_INTERVAL = 2  # Minimum 2 seconds between API calls
last_signal_state = None  # Track last signal to avoid redundant calls
quota_reset_time = None  # Track when quota resets
api_call_count = 0  # Track API calls for debugging

# Initialize Gemini
try:
    import google.generativeai as genai
    from google.generativeai import types
    
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    print(GEMINI_API_KEY)
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
        model = "gemini-2.0-flash"
        logger.info("Gemini API initialized with API key")
    else:
        logger.warning("GEMINI_API_KEY not set. Using rule-based decisions.")
        model = None
except (ImportError, Exception) as e:
    logger.warning(f"Gemini not available: {e}. Using rule-based decisions.")
    model = None

def ask_llm(signal, rsi, volatility):
    """Get trading decision from Google Gemini LLM with smart caching"""
    global last_api_call, api_call_count
    
    print("hey i am in genai")
    # Extract values
    signal_val = signal
    rsi_val = float(rsi.iloc[0]) if hasattr(rsi, 'iloc') else float(rsi)
    volatility_val = float(volatility.iloc[0]) if hasattr(volatility, 'iloc') else float(volatility)
    
    # Create cache key based on inputs
    cache_key = hashlib.md5(f"{signal_val}_{rsi_val:.4f}_{volatility_val:.6f}".encode()).hexdigest()
    
    # Check cache first
    if cache_key in response_cache:
        cached_time, cached_response = response_cache[cache_key]
        if datetime.now() - cached_time < timedelta(seconds=CACHE_TTL):
            logger.info(f"Using cached response (no API call) - API calls today: {api_call_count}")
            return cached_response
    
    # If no API key, use rule-based fallback
    if model is None:
        return _rule_based_decision(signal_val, rsi_val, volatility_val)
    
    # **KEY OPTIMIZATION: Only call LLM if signal changed**
    if not should_call_llm(signal_val):
        logger.info(f"Signal unchanged ({signal_val}) - using rule-based decision to save API quota")
        return _rule_based_decision(signal_val, rsi_val, volatility_val)
    
    try:
        # Rate limiting - enforce minimum interval between API calls
        if last_api_call is not None:
            elapsed = time.time() - last_api_call
            if elapsed < MIN_INTERVAL:
                wait_time = MIN_INTERVAL - elapsed
                logger.info(f"Rate limiting: waiting {wait_time:.2f}s before next API call")
                time.sleep(wait_time)
        
        # Prompt for Gemini
        print("hey i am here")
        prompt = f"""You are a professional stock trader AI. Analyze the following market indicators and provide a trading decision.

MARKET DATA:
- ML Signal: {signal_val}
- RSI (Relative Strength Index): {rsi_val:.2f}
- Volatility: {volatility_val:.4f}

Based on these indicators, provide your trading decision in this EXACT format:
Decision: [BUY/SELL/HOLD]
Confidence: [HIGH/MEDIUM/LOW]
Reason: [Brief explanation]

Consider:
- ML Signal accuracy
- RSI overbought (>70) / oversold (<30) conditions
- Volatility risk levels
- Risk/reward ratio"""
        
        last_api_call = time.time()
        api_call_count += 1
        
        model_obj = genai.GenerativeModel(model)
        response = model_obj.generate_content(prompt)
        decision_text = response.text.strip()
        
        # Cache successful response
        response_cache[cache_key] = (datetime.now(), decision_text)
        
        logger.info(f"Gemini Decision (API call #{api_call_count}): {decision_text}")
        return decision_text
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        # Check if it's a quota error
        if "429" in str(e) or "quota" in str(e).lower():
            logger.warning("Quota exceeded. Falling back to rule-based decision (quota resets in ~24 hours).")
            # Set a reminder for quota reset
            global quota_reset_time
            quota_reset_time = datetime.now() + timedelta(hours=24)
        return _rule_based_decision(signal_val, rsi_val, volatility_val)

def should_call_llm(signal_val):
    """Only call LLM if signal changes to reduce API calls"""
    global last_signal_state
    
    # Call LLM if:
    # 1. Signal changed from last state
    # 2. Or haven't called in over 30 minutes (refresh decision)
    signal_changed = last_signal_state != signal_val
    if signal_changed:
        last_signal_state = signal_val
        return True
    return False

def _rule_based_decision(signal_val, rsi_val, volatility_val):
    """Fallback rule-based decision system"""
    if signal_val == "BUY" and rsi_val < 70 and volatility_val < 0.05:
        decision = "BUY"
        confidence = "HIGH"
        reason = f"BUY signal with healthy RSI ({rsi_val:.2f}) and low volatility"
    elif signal_val == "SELL" and rsi_val > 30:
        decision = "SELL"
        confidence = "MEDIUM"
        reason = f"SELL signal confirmed by RSI ({rsi_val:.2f})"
    else:
        decision = "HOLD"
        confidence = "LOW"
        reason = f"Conditions not favorable: Signal={signal_val}, RSI={rsi_val:.2f}, Vol={volatility_val:.4f}"
    
    return f"Decision: {decision}\nConfidence: {confidence}\nReason: {reason}"
