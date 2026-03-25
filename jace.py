import pandas as pd
import os
from datetime import datetime
import numpy as np

def execute_trade(asset, current_price, average, rsi, hook, ledger_df, risk_multiplier=50, **kwargs):
    """
    Jace: High-Precision Execution Agent (Sentinel 2.1).
    UPDATED: Now using **kwargs to prevent Streamlit Tab crashes.
    """
    # ... rest of your code remains the same ...
    # --- TICKER BRIDGE ---
    ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HEDERA": "HBAR", "HBAR": "HBAR"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- DYNAMIC RISK PARAMETERS ---
    try:
        # Pull the last known balance from the ledger
        tradable_balance = ledger_df['Tradable_Balance'].iloc[-1] if 'Tradable_Balance' in ledger_df.columns else 1000.0
        
        # RISK SCALING LOGIC:
        # If Risk is 100 (Max), risk_factor becomes 0 (No trade).
        # If Risk is 0 (Safe), risk_factor becomes 1.0 (Full 20% wager).
        risk_factor = (100 - risk_multiplier) / 100
        
        base_wager = float(tradable_balance) * 0.20 
        WAGER_SIZE = base_wager * risk_factor
        
    except Exception:
        WAGER_SIZE = 50.0  # Safe fallback if ledger reading fails

    STOP_LOSS_PCT = 3.5      
    PROFIT_THRESHOLD = 2.0    
    TRAILING_PCT = 10.0      
    SNAP_THRESHOLD = -2.0    

    if current_price is None or average is None or average == 0:
        return "WAITING", None

    # --- 1. ACTIVE TRADE MONITORING ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            mask = (ledger_df['asset'].str.upper() == search_asset) & (ledger_df['result_clean'].str.upper() == 'OPEN')
            
            if mask.any():
                trade_idx = ledger_df[mask].index[-1]
                entry_price = float(ledger_df.at[trade_idx, 'price'])
                peak_price = float(ledger_df.at[trade_idx, 'result']) 
                
                new_peak = max(current_price, peak_price)
                perf_from_entry = ((current_price - entry_price) / entry_price) * 100
                perf_from_peak = ((current_price - new_peak) / new_peak) * 100
                total_pnl_pct = ((current_price / entry_price) * 100) - 100

                # EXIT LOGIC
                hit_stop = perf_from_entry <= -STOP_LOSS_PCT
                is_in_profit_zone = perf_from_entry >= PROFIT_THRESHOLD
                hit_trail = is_in_profit_zone and (perf_from_peak <= -TRAILING_PCT)
                hit_rsi_exit = is_in_profit_zone and (rsi > 70) 

                if hit_stop or hit_trail or hit_rsi_exit:
                    reason = "EMERGENCY_STOP" if hit_stop else "TRAILING_PROFIT"
                    if hit_rsi_exit: reason = "RSI_MOMENTUM_EXIT"
                    
                    trade_update = {
                        "index": trade_idx,
                        "price": current_price,
                        "profit_usd": total_pnl_pct,
                        "reason": reason
                    }
                    return "CLOSE", trade_update
                
                if new_peak > peak_price:
                    return "PEAK_UPDATE", {"index": trade_idx, "new_peak": new_peak}
                
                return "HOLDING", {"pnl": total_pnl_pct}
                
        except Exception as e:
            print(f"🏛️ JACE AUDIT ERROR: {e}")

    # --- 2. NEW TRADE ANALYSIS (ENTRY) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # Only Buy if we actually have a Wager Size (Risk hasn't zeroed us out)
    if snap_pct <= SNAP_THRESHOLD and hook and WAGER_SIZE > 0:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade_info = [ts, search_asset, "BUY", current_price, WAGER_SIZE, current_price, 0.0, "OPEN"]
        return "BUY", trade_info

    return "SCANNING", None
