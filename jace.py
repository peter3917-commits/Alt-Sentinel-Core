import pandas as pd
import os
from datetime import datetime
import numpy as np

def execute_trade(asset, current_price, average, rsi, hook, ledger_df, risk_multiplier=50, **kwargs):
    """
    Jace: High-Precision Execution Agent (Sentinel 2.1).
    FIXED: Case-sensitivity on 'tradable_balance' to match Piper's output.
    """
    
    # --- TICKER BRIDGE ---
    ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HEDERA": "HBAR", "HBAR": "HBAR"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- DYNAMIC RISK PARAMETERS ---
    try:
        # Piper standardizes columns to lowercase. We must match that here.
        if ledger_df is not None and 'tradable_balance' in ledger_df.columns:
            balance = float(ledger_df['tradable_balance'].iloc[-1])
        else:
            balance = 1000.0 # Default starting capital
            
        # RISK SCALING LOGIC:
        # Claw provides 0-100. We invert it so 100 Risk = 0 Wager.
        risk_factor = max(0, (100 - float(risk_multiplier)) / 100)
        
        # We risk 20% of balance, scaled by Claw's sentiment
        base_wager = balance * 0.20 
        WAGER_SIZE = round(base_wager * risk_factor, 2)
        
    except Exception:
        WAGER_SIZE = 50.0  # Safe fallback 

    # --- STRATEGY THRESHOLDS ---
    STOP_LOSS_PCT = 3.5      
    PROFIT_THRESHOLD = 2.0    
    TRAILING_PCT = 10.0      
    SNAP_THRESHOLD = -2.0    

    if current_price is None or average is None or average == 0:
        return "WAITING", None

    # --- 1. ACTIVE TRADE MONITORING ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            # Match assets and check for 'OPEN' status (lowercased by Piper)
            mask = (ledger_df['asset'].astype(str).str.upper() == search_asset) & \
                   (ledger_df['status_check'].astype(str).str.upper() == 'OPEN')
            
            if mask.any():
                trade_idx = ledger_df[mask].index[-1]
                entry_price = float(ledger_df.at[trade_idx, 'price'])
                # 'result' column stores the peak price while trade is OPEN
                peak_price = float(ledger_df.at[trade_idx, 'result']) 
                
                new_peak = max(current_price, peak_price)
                perf_from_entry = ((current_price - entry_price) / entry_price) * 100
                perf_from_peak = ((current_price - new_peak) / new_peak) * 100
                total_pnl_pct = perf_from_entry

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
                
        except Exception:
            pass # Keep silent in Streamlit production

    # --- 2. NEW TRADE ANALYSIS (ENTRY) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # Only Buy if we have a Wager Size and technical triggers hit
    if snap_pct <= SNAP_THRESHOLD and hook and WAGER_SIZE > 0:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Format: Timestamp, Asset, Type, Price, Wager, Result(Peak), Profit, Status
        trade_info = [ts, search_asset, "BUY", current_price, WAGER_SIZE, current_price, 0.0, "OPEN"]
        return "BUY", trade_info

    return "SCANNING", None
