import os
import logging

logger = logging.getLogger(__name__)

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
    """Get trading decision from Google Gemini LLM"""
    print("hey i am in genai")
    # Extract values
    signal_val = signal
    rsi_val = float(rsi.iloc[0]) if hasattr(rsi, 'iloc') else float(rsi)
    volatility_val = float(volatility.iloc[0]) if hasattr(volatility, 'iloc') else float(volatility)
    
    # If no API key, use rule-based fallback
    if model is None:
        return _rule_based_decision(signal_val, rsi_val, volatility_val)
    
    try:
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
        
        model_obj = genai.GenerativeModel(model)
        response = model_obj.generate_content(prompt)
        decision_text = response.text.strip()
        logger.info(f"Gemini Decision: {decision_text}")
        return decision_text
        
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return _rule_based_decision(signal_val, rsi_val, volatility_val)

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
