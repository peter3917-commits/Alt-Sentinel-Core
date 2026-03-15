import pandas as pd
import os
from datetime import datetime
import numpy as np

def execute_trade(asset, current_price, average, rsi, hook, ledger_df):
    """
    Jace: High-Precision Execution Agent (Sentinel 2.1).
    Focus: Dynamic Position Sizing (20% Tradable Balance) & Ratchet Profit Management.
    Policy: Auto-scale wager based on Cash - (Tax + Costs).
    """
    # --- TICKER BRIDGE ---
    ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HEDERA": "HBAR", "HBAR": "HBAR"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- DYNAMIC RISK PARAMETERS ---
    # We now derive WAGER_SIZE from the Ledger's 'Tradable_Balance'
    try:
        # Assumes your Ledger has a 'Tradable_Balance' column or a specific summary row
        # If not found, it defaults to 100 to ensure the 'Company' never stalls
        tradable_balance = ledger_df['Tradable_Balance'].iloc[-1] if 'Tradable_Balance' in ledger_df.columns else 1000.0
        WAGER_SIZE = float(tradable_balance) * 0.20 
    except Exception:
        WAGER_SIZE = 100.0  # Safety fallback

    STOP_LOSS_PCT = 3.5      # Fixed -3.5% Emergency Stop Loss from Entry
    PROFIT_THRESHOLD = 2.0    # Initial 2% profit target before RSI/Trailing act
    TRAILING_PCT = 10.0      # 10% Trailing Profit from the Peak (High-Water Mark)
    SNAP_THRESHOLD = -2.0    # Kael's Snap trigger requirement

    # --- SAFETY SHIELD ---
    if current_price is None or average is None or average == 0:
        return "WAITING", None

    # --- 1. ACTIVE TRADE MONITORING (LEDGER RECONCILIATION) ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            # Search for an OPEN trade for this specific asset
            mask = (ledger_df['asset'].str.upper() == search_asset) & (ledger_df['result_clean'].str.upper() == 'OPEN')
            
            if mask.any():
                # Get the most recent open trade
                trade_idx = ledger_df[mask].index[-1]
                entry_price = float(ledger_df.at[trade_idx, 'price'])
                
                # 'result' column stores our 'High-Water Mark' (Peak Price)
                peak_price = float(ledger_df.at[trade_idx, 'result']) 
                
                # Update Peak Price if the current price is higher (The Ratchet)
                new_peak = max(current_price, peak_price)
                
                # PERFORMANCE CALCULATIONS
                perf_from_entry = ((current_price - entry_price) / entry_price) * 100
                perf_from_peak = ((current_price - new_peak) / new_peak) * 100
                total_pnl_pct = ((current_price / entry_price) * 100) - 100

                # --- EXIT LOGIC ---
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
                
                # --- PEAK UPDATE ---
                if new_peak > peak_price:
                    return "PEAK_UPDATE", {"index": trade_idx, "new_peak": new_peak}
                
                return "HOLDING", {"pnl": total_pnl_pct}
                
        except Exception as e:
            print(f"🏛️ JACE AUDIT ERROR: {e}")

    # --- 2. NEW TRADE ANALYSIS (ENTRY) ---
    snap_pct = ((current_price - average) / average) * 100
    
    if snap_pct <= SNAP_THRESHOLD and hook:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # WAGER_SIZE is now the dynamic 20% calculated at the start of the function
        trade_info = [ts, search_asset, "BUY", current_price, WAGER_SIZE, current_price, 0.0, "OPEN"]
        return "BUY", trade_info

    return "SCANNING", None
