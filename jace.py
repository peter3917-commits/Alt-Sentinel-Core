import pandas as pd
import os
from datetime import datetime
import numpy as np

def execute_trade(asset, current_price, average, rsi, hook, ledger_df):
    """
    Jace: High-Precision Execution Agent (Sentinel 2.0).
    Focus: Execution of the £100 wager and managing the Trailing Profit ratchet.
    """
    # --- TICKER BRIDGE ---
    ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HEDERA": "HBAR", "HBAR": "HBAR"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- INSTITUTIONAL SETTINGS ---
    WAGER_SIZE = 100.0        # Fixed £100 wager per trade
    STOP_LOSS_PCT = 3.5      # Fixed -3.5% Emergency Stop Loss from Entry
    TRAILING_PCT = 10.0      # 10% Trailing Profit from the Peak (High-Water Mark)
    SNAP_THRESHOLD = -2.0    # Kael's Snap trigger requirement

    # --- SAFETY SHIELD ---
    if current_price is None or average is None or average == 0:
        return "WAITING", None

    # --- 1. ACTIVE TRADE MONITORING (LEDGER RECONCILIATION) ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            # Search for an OPEN trade for this specific asset
            # We use 'result_clean' to check status and 'asset' for the ticker
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
                # A: Fixed Stop Loss (If it drops immediately)
                hit_stop = perf_from_entry <= -STOP_LOSS_PCT
                
                # B: Trailing Profit (If it rose and then dropped 10% from peak)
                hit_trail = perf_from_peak <= -TRAILING_PCT
                
                # C: Fatigue Overheat (RSI Exhaustion)
                hit_rsi_overheat = rsi > 75

                if hit_stop or hit_trail or hit_rsi_overheat:
                    reason = "STOP_LOSS" if hit_stop else "TRAILING_PROFIT"
                    if hit_rsi_overheat: reason = "RSI_EXHAUSTION"
                    
                    trade_update = {
                        "index": trade_idx,
                        "price": current_price,
                        "profit_usd": total_pnl_pct,
                        "reason": reason
                    }
                    return "CLOSE", trade_update
                
                # --- PEAK UPDATE ---
                # If no exit, but the price hit a new high, tell Piper to move the goalposts
                if new_peak > peak_price:
                    return "PEAK_UPDATE", {"index": trade_idx, "new_peak": new_peak}
                
                return "HOLDING", {"pnl": total_pnl_pct}
                
        except Exception as e:
            print(f"🏛️ JACE AUDIT ERROR: {e}")

    # --- 2. NEW TRADE ANALYSIS (ENTRY) ---
    # Jace only acts if Kael’s intelligence confirms the Snap AND the Hook
    snap_pct = ((current_price - average) / average) * 100
    
    # Kael's Entry Condition: Deep Snap + Price Turning Up (Hook)
    if snap_pct <= SNAP_THRESHOLD and hook:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Ledger Columns: [timestamp, asset, type, price, wager, result (peak), profit, result_clean]
        trade_info = [ts, search_asset, "BUY", current_price, WAGER_SIZE, current_price, 0.0, "OPEN"]
        return "BUY", trade_info

    return "SCANNING", None
