import pandas as pd
import os
from datetime import datetime
import numpy as np

def calculate_wma(prices, period=5):
    """Jace's (formerly Lawrence) Weighted Moving Average for the trailing exit."""
    if len(prices) < period:
        return prices[-1]
    weights = np.arange(1, period + 1)
    return (prices[-period:] * weights).sum() / weights.sum()

def execute_trade(asset, current_price, average, rsi=None, history_df=None, ledger_df=None):
    """
    Jace: High-Precision Execution Agent.
    Handles trade entries and exits for the Alt-Sentinel sector.
    """
    # --- TICKER BRIDGE: ALT-SENTINEL SECTOR ---
    ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HEDERA": "HBAR", "HBAR": "HBAR"}
    search_asset = ticker_map.get(asset.upper(), asset).upper()

    # --- INSTITUTIONAL SETTINGS ---
    # Precision is vital here for sub-dollar bid/ask spreads
    ask_price = current_price * 1.0001 if current_price else 0
    bid_price = current_price * 0.9999 if current_price else 0
    TOTAL_BANK = 1000.0  
    WAGER_SIZE = TOTAL_BANK * 0.10 
    
    TRIGGER_THRESHOLD = 1.5  
    STOP_LOSS_PCT = 1.5      
    TARGET_OVER_MAGNET = 10.0 
    
    # --- SAFETY SHIELD ---
    if current_price is None or average is None or average == 0 or history_df is None:
        return 0.0, 0.0, "WAITING", None

    # --- INDICATOR PREP ---
    cols_lower = [c.lower() for c in history_df.columns]
    if 'balance' in cols_lower:
        price_col = history_df.columns[cols_lower.index('balance')]
    elif 'price_usd' in cols_lower:
        price_col = history_df.columns[cols_lower.index('price_usd')]
    else:
        return 0.0, 0.0, "DATA_ERROR", None

    prices_arr = history_df[price_col].values
    ema_5 = history_df[price_col].ewm(span=5, adjust=False).mean().iloc[-1]
    wma_5 = calculate_wma(prices_arr, period=5)

    # --- 1. ACTIVE TRADE MONITORING (CLOUD LEDGER) ---
    if ledger_df is not None and not ledger_df.empty:
        try:
            df = ledger_df.copy()
            df.columns = [c.lower().strip() for c in df.columns]
            
            for i in range(len(df)):
                csv_asset = str(df.iloc[i]['asset']).strip().upper()
                is_open = str(df.iloc[i]['result']).strip().upper() == 'OPEN'
                
                if is_open and csv_asset == search_asset:
                    entry_price = float(df.iloc[i]['price'])
                    # Performance calculation for low-price assets
                    perf = ((bid_price - entry_price) / entry_price) * 100
                    
                    # Exit Condition Logic
                    hit_moonshot = (bid_price >= average * (1 + (TARGET_OVER_MAGNET / 100)))
                    hit_magnet_trend_break = (bid_price >= average and bid_price < wma_5)
                    hit_stop = (perf <= -STOP_LOSS_PCT)

                    outcome = "OPEN"
                    exit_triggered = False

                    if hit_moonshot:
                        outcome, exit_triggered = "WIN_MOONSHOT", True
                    elif hit_magnet_trend_break:
                        outcome, exit_triggered = "WIN_TRAILING", True
                    elif hit_stop:
                        outcome, exit_triggered = "LOSS", True

                    if exit_triggered:
                        pnl_val = WAGER_SIZE * (perf / 100)
                        trade_update = {
                            "index": i,
                            "result": outcome,
                            "profit_usd": pnl_val
                        }
                        return pnl_val, pnl_val, outcome, trade_update
                    
                    return 0.0, WAGER_SIZE * (perf / 100), "OPEN", None
        except Exception as e:
            print(f"Jace Audit Error: {e}")

    # --- 2. NEW TRADE ANALYSIS ---
    snap_pct = ((current_price - average) / average) * 100
    fast_hook = current_price > ema_5
    can_buy = (snap_pct <= -TRIGGER_THRESHOLD) and fast_hook and (rsi is not None and rsi < 35)

    # --- 3. EXECUTION ---
    if can_buy:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # Ticker, Price, and Wager size remain the core buy data
        trade_info = [ts, search_asset, "BUY", ask_price, WAGER_SIZE, "OPEN", 0.0]
        return 0.0, 0.0, "BUY", trade_info

    return 0.0, 0.0, "HOLD", None
