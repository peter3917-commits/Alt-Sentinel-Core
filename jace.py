import pandas as pd
import os
from datetime import datetime
import numpy as np

def calculate_rsi(series, period=100):
    """100-Point RSI for smoothed trend analysis."""
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def calculate_wma(prices, period=5):
    """Jace's Weighted Moving Average."""
    if len(prices) < period:
        return prices[-1]
    weights = np.arange(1, period + 1)
    return (prices[-period:] * weights).sum() / weights.sum()

def execute_trade(asset, current_price, average, history_df=None, ledger_df=None):
    """
    Jace: High-Precision Execution Agent (Sentinel 2.0).
    Now with 100pt RSI Crossover, £100 fixed wagers, and 10% Trailing Profits.
    """
    # --- TICKER BRIDGE ---
    ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HEDERA": "HBAR", "HBAR": "HBAR"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- INSTITUTIONAL SETTINGS ---
    WAGER_SIZE = 100.0        # Fixed £100 wager
    STOP_LOSS_PCT = 3.5      # Fixed -3.5% Stop Loss
    TRAILING_PCT = 10.0      # 10% Trailing Profit from Peak
    SNAP_THRESHOLD = -2.0    # Entry trigger at -2% below Magnet

    # --- SAFETY SHIELD ---
    if current_price is None or average is None or average == 0 or history_df is None:
        return 0.0, 0.0, "WAITING", None

    # --- INDICATOR PREP ---
    history_df['rsi_100'] = calculate_rsi(history_df['Balance'], period=100)
    current_rsi = history_df['rsi_100'].iloc[-1]
    prev_rsi = history_df['rsi_100'].iloc[-2] if len(history_df) > 1 else current_rsi
    
    # --- 1. ACTIVE TRADE MONITORING (LEDGER) ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            # Normalize ledger for searching
            df = ledger_df.copy()
            df.columns = [c.lower().strip() for c in df.columns]
            
            for i in range(len(df)):
                csv_asset = str(df.iloc[i]['asset']).strip().upper()
                # We use 'result_clean' (col 8) to check if OPEN
                is_open = str(df.iloc[i]['result_clean']).strip().upper() == 'OPEN'
                
                if is_open and csv_asset == search_asset:
                    entry_price = float(df.iloc[i]['price'])
                    # Peak Price is stored in the 'result' column (col 6)
                    peak_price = float(df.iloc[i]['result']) 
                    
                    # Update Peak Price in real-time
                    new_peak = max(current_price, peak_price)
                    perf_from_entry = ((current_price - entry_price) / entry_price) * 100
                    perf_from_peak = ((current_price - new_peak) / new_peak) * 100

                    # EXIT LOGIC
                    hit_stop = perf_from_entry <= -STOP_LOSS_PCT
                    hit_trail = perf_from_peak <= -TRAILING_PCT
                    hit_rsi_overheat = current_rsi > 75

                    if hit_stop or hit_trail or hit_rsi_overheat:
                        outcome = "LOSS" if hit_stop else "WIN_TRAIL"
                        if hit_rsi_overheat: outcome = "WIN_RSI"
                        
                        qty = WAGER_SIZE / entry_price
                        final_pnl = (qty * current_price) - WAGER_SIZE
                        
                        trade_update = {
                            "index": i,
                            "price": current_price,
                            "profit_usd": final_pnl,
                            "result_clean": "CLOSED"
                        }
                        return final_pnl, final_pnl, outcome, trade_update
                    
                    # If no exit, update the Peak Price in Ledger if it moved up
                    if new_peak > peak_price:
                        return 0.0, 0.0, "PEAK_UPDATE", {"index": i, "new_peak": new_peak}
                    
                    return 0.0, 0.0, "OPEN", None
        except Exception as e:
            print(f"Jace Audit Error: {e}")

    # --- 2. NEW TRADE ANALYSIS (ENTRY) ---
    snap_pct = ((current_price - average) / average) * 100
    
    # Trigger: Price is snapped AND RSI was < 35 and just crossed back up
    can_buy = (snap_pct <= SNAP_THRESHOLD) and (prev_rsi < 35 and current_rsi >= 35)

    # --- 3. EXECUTION ---
    if can_buy:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Columns: timestamp, asset, type, price, wager, result (peak), profit, result_clean
        trade_info = [ts, search_asset, "BUY", current_price, WAGER_SIZE, current_price, 0.0, "OPEN"]
        return 0.0, 0.0, "BUY", trade_info

    return 0.0, 0.0, "SCANNING", None
