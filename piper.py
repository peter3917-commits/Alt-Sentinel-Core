import pandas as pd
import os
from datetime import datetime

# --- ALT-SENTINEL FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(conn, prices_dict=None):
    """
    Piper: The High-Precision Accountant.
    Fetches live Ledger from Google Sheets and calculates metrics for Alt-Sentinel.
    """
    default_data = {"vault_cash": INITIAL_CAPITAL, "tradable_balance": INITIAL_CAPITAL, "tax_pot": 0.0, "burn": 0.0, "trades_df": pd.DataFrame()}
    
    try:
        # STEP 1: Fresh Ledger Fetch
        df = conn.read(worksheet="Ledger", ttl="0")
        
        if df.empty:
            return default_data

        # Clean column names
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Ensure numeric columns are floats (preserving 6dp for XRP/XLM prices)
        for col in ['profit_usd', 'wager', 'price']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        df['result_clean'] = df['result'].astype(str).str.lower().str.strip()
        win_labels = ['win', 'win_moonshot', 'win_trailing']
        
        # Calculate Realized P/L
        realized = float(df[df['result_clean'].isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # Calculate Overheads (Burn)
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(pd.to_numeric(overhead_df['amount'], errors='coerce').abs().sum())
            except: burn = 0.0

        tax_pot = float(df[df['result_clean'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT)
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        locked_wagers = float(df[df['result_clean'] == 'open']['wager'].sum())

        return {
            "vault_cash": vault_cash,
            "tradable_balance": float(vault_cash - tax_pot - locked_wagers),
            "tax_pot": tax_pot, 
            "burn": burn, 
            "trades_df": df
        }
    except Exception as e:
        print(f"🏛️ PIPER CRITICAL LEDGER ERROR: {e}")
        return default_data

def get_live_price(asset, prices_dict):
    """FORCED MATCHING with High-Precision Cleaning."""
    if not isinstance(prices_dict, dict) or not prices_dict: 
        return None
    
    search_asset = str(asset).strip().upper()
    
    clean_prices = {}
    for k, v in prices_dict.items():
        if v is not None:
            try:
                # Precision Shield: Ensure we don't round off the micro-cents
                val = float(str(v).replace(',', '').replace('$', '').strip())
                clean_prices[str(k).strip().upper()] = val
            except:
                continue
    
    if search_asset in clean_prices:
        return clean_prices[search_asset]
            
    # --- ALT-SENTINEL ASSET BRIDGE ---
    xr = {
        "XRP": "RIPPLE", 
        "XLM": "STELLAR", 
        "HBAR": "HEDERA", 
        "STELLAR": "XLM", 
        "HEDERA": "HBAR"
    }
    target = xr.get(search_asset)
    
    if target and target in clean_prices:
        return clean_prices[target]
        
    return None

def calculate_unrealized(trades_df, prices_dict):
    if trades_df is None or trades_df.empty:
        return 0.0, pd.DataFrame()
    
    unreal_total = 0.0
    trades_df['result_clean'] = trades_df['result'].astype(str).str.lower().str.strip()
    open_trades = trades_df[trades_df['result_clean'] == 'open'].copy()
    
    for idx, row in open_trades.iterrows():
        live_p = get_live_price(row.get('asset', 'UNKNOWN'), prices_dict)
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if live_p is not None and entry_p > 0:
            # P/L logic for micro-movements
            pnl = wager * ((live_p - entry_p) / entry_p)
            unreal_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl
    return float(unreal_total), open_trades

def format_institutional_ledger(df, prices_dict):
    if df is None or df.empty: return pd.DataFrame()
    report = []
    now = datetime.now().replace(tzinfo=None)
    df['result_clean'] = df['result'].astype(str).str.lower().str.strip()
    
    for _, row in df.iterrows():
        asset_name = str(row.get('asset', '???')).strip().upper()
        res_clean = row.get('result_clean', 'unknown')
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if res_clean in ['open', 'active']:
            status = "🟢 ACTIVE"
            live_p = get_live_price(asset_name, prices_dict)
            mtm = float(live_p) if live_p is not None else entry_p
            pnl = wager * ((mtm - entry_p) / entry_p) if entry_p > 0 else 0
        else:
            status = "✅ CLOSED"
            pnl = float(row.get('profit_usd', 0))
            # Backward calculate MTM based on recorded P/L
            mtm = entry_p * (1 + (pnl / wager)) if wager > 0 else entry_p
            
        ret_pct = (pnl / wager) * 100 if wager > 0 else 0
        try:
            ts = pd.to_datetime(row.get('timestamp')).tz_localize(None)
            diff = now - ts
            age_str = f"{diff.days}d {diff.seconds // 3600}h"
        except: age_str = "---"

        report.append({
            "Ticker": asset_name, 
            "Status": status, 
            "Age": age_str,
            "Entry Price": entry_p, # main.py will format this to 6dp
            "MTM Price": mtm,
            "Return (%)": ret_pct, 
            "P/L ($)": pnl
        })
    return pd.DataFrame(report)
