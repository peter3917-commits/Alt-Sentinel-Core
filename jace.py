import pandas as pd
import os
from datetime import datetime
import numpy as np

def execute_trade(asset, current_price, average, rsi, hook, ledger_df, risk_multiplier=50, **kwargs):
    """
    Jace: High-Precision Execution Agent (Sentinel 2.2).
    CALIBRATED: Optimized for Claw 2.1 Macro-Risk scaling.
    """
    
    # --- TICKER BRIDGE ---
    ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HBAR": "HBAR", "HBAR": "HBAR"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- DYNAMIC RISK PARAMETERS (The 'Macro Valve') ---
    try:
        if ledger_df is not None and 'tradable_balance' in ledger_df.columns:
            balance = float(ledger_df['tradable_balance'].iloc[-1])
        else:
            balance = 1000.0 # Institutional Default
            
        # 🏛️ MACRO RISK SCALING LOGIC:
        # risk_multiplier now comes from Claw's Fear & Greed Inversion.
        # High Risk Multiplier (Extreme Fear) = Lower Wager Size.
        risk_factor = max(0, (100 - float(risk_multiplier)) / 100)
        
        # We maintain the 20% Base Risk rule, scaled by the 'Macro Vibe'.
        base_wager = balance * 0.20 
        WAGER_SIZE = round(base_wager * risk_factor, 2)
        
    except Exception:
        WAGER_SIZE = 50.0  # Conservative Fallback 

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
            mask = (ledger_df['asset'].astype(str).str.upper() == search_asset) & \
                   (ledger_df['status_check'].astype(str).str.upper() == 'OPEN')
            
            if mask.any():
                trade_idx = ledger_df[mask].index[-1]
                entry_price = float(ledger_df.at[trade_idx, 'price'])
                peak_price = float(ledger_df.at[trade_idx, 'result']) 
                
                new_peak = max(current_price, peak_price)
                perf_from_entry = ((current_price - entry_price) / entry_price) * 100
                perf_from_peak = ((current_price - new_peak) / new_peak) * 100
                total_pnl_pct = perf_from_entry

                # EXIT LOGIC (Momentum Hunter Protocol)
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
            pass 

    # --- 2. NEW TRADE ANALYSIS (ENTRY) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # 🏛️ THE 'HOOK' RESTRAINT: 
    # Must be -2.0% below the Magnet AND moving upwards (hook) AND have a non-zero wager.
    if snap_pct <= SNAP_THRESHOLD and hook and WAGER_SIZE > 0:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        trade_info = [ts, search_asset, "BUY", current_price, WAGER_SIZE, current_price, 0.0, "OPEN"]
        return "BUY", trade_info

    return "SCANNING", None

    return "SCANNING", None
