import pandas as pd
import numpy as np

def calculate_rsi(prices, period=100):
    """
    Kael's (formerly Arthur) sense of 'Overstretched' markets using RSI logic.
    Using a 100-period window for deep-trend fatigue analysis.
    """
    if len(prices) < period + 1:
        return 50.0  # Neutral starting point
    
    delta = pd.Series(prices).diff()
    
    # Kael uses the Simple Moving Average version of RSI for smoother, 
    # institutional-grade fatigue signals rather than jittery retail RSI.
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Replace zeros to prevent division errors
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    
    # Return the latest value, handle NaN by returning neutral 50
    val = rsi.iloc[-1]
    return float(val) if not np.isnan(val) else 50.0

def check_for_snap(asset, current_price, history_df):
    """
    Kael: The High-Precision Analyst.
    Responsible for identifying the 'Magnet' and the 'Hook'.
    
    Returns: (moving_avg, snap_pct, rsi_value, hook_detected)
    """
    
    # Identify the correct column from Vance's data
    price_col = 'balance' if 'balance' in history_df.columns else 'price_usd'
    
    # Safety Check: If no data, return neutral values to prevent firm crash
    if history_df.empty or price_col not in history_df.columns:
        return None, 0.0, 50.0, False

    # 1. THE MAGNET (24h Moving Average)
    # 24 hours * 12 pings/hour (at 5-min intervals) = 288 data points
    moving_avg = history_df[price_col].tail(288).mean()
    
    # 2. THE SNAP (Distance from Magnet)
    # Calculated to high precision to catch micro-deviations in XRP/HBAR/XLM
    snap_pct = ((current_price - moving_avg) / moving_avg) * 100
    
    # 3. THE FATIGUE (RSI Calculation)
    rsi_value = calculate_rsi(history_df[price_col], period=100)
    
    # 4. THE PATIENCE (The Hook Detection)
    # This is the "Turn-up" indicator. Jace only buys when this is True.
    last_recorded_price = history_df[price_col].iloc[-1]
    hook_detected = current_price > last_recorded_price

    # --- 🏛️ KAEL'S CONSOLE REPORT ---
    # High-precision audit: reporting with 6 decimal places for price 
    # and 4 for snap to ensure visibility of small movements.
    if abs(snap_pct) >= 1.5 and rsi_value < 35.0:
        status = "HOOKED 🪝" if hook_detected else "FALLING 🔪"
        print(f"🏛️ KAEL: {asset} at ${current_price:.6f} is {snap_pct:.4f}% from Magnet | RSI: {rsi_value:.1f} | {status}")
    
    return moving_avg, snap_pct, rsi_value, hook_detected
