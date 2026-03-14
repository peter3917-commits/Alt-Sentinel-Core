import pandas as pd
import os
from datetime import datetime

# --- ALT-SENTINEL FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(conn, prices_dict=None):
    """
    Piper: The High-Precision Accountant.
    Updated to handle the 'Result' column as a Peak Price for Trailing Stops.
    """
    default_data = {"vault_cash": INITIAL_CAPITAL, "tradable_balance": INITIAL_CAPITAL, "tax_pot": 0.0, "burn": 0.0, "trades_df": pd.DataFrame()}
    
    try:
        # STEP 1: Fresh Ledger Fetch
        df = conn.read(worksheet="Ledger", ttl="0")
        
        if df.empty:
            return default_data

        # Clean column names
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Ensure numeric columns are floats (preserving 6dp for precision sectors)
        for col in ['profit_usd', 'wager', 'price', 'result']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # --- THE PEAK TRACKING FIX ---
        # result_clean is our Status (OPEN/CLOSED). 
        # result is now the Peak Price used by Jace for the 10% Trailing Profit.
        df['status_check'] = df['result_clean'].astype(str).str.lower().str.strip()
        win_labels = ['win', 'win_moonshot', 'win_trailing', 'trail_exit', 'closed']
        
        # Calculate Realized P/L (Only from CLOSED/WIN/LOSS trades)
        realized = float(df[df['status_check'].isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # Calculate Overheads (Burn)
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(pd.to_numeric(overhead_df['amount'], errors='coerce').abs().sum())
            except: burn = 0.0

        # Tax Reserve calculation
        tax_pot = float(df[df['status_check'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT)
        if tax_pot < 0: tax_pot = 0.0 # Don't take tax on net losses
        
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # Deduct wagers for currently OPEN trades (Case-insensitive check)
        locked_wagers = float(df[df['status_check'] == 'open']['wager'].sum())

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
    """FORCED MATCHING with High-Precision Cleaning for XRP/XLM/HBAR."""
    if not isinstance(prices_dict, dict) or not prices_dict: 
        return None
    
    search_asset = str(asset).strip().upper()
    
    clean_prices = {}
    for k, v in prices_dict.items():
        if v is not None:
            try:
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
    """Calculates floating P/L for the dashboard."""
    if trades_df is None or trades_df.empty:
        return 0.0, pd.DataFrame()
    
    unreal_total = 0.0
    trades_df['status_check'] = trades_df['result_clean'].astype(str).str.lower().str.strip()
    open_trades = trades_df[trades_df['status_check'] == 'open'].copy()
    
    for idx, row in open_trades.iterrows():
        live_p = get_live_price(row.get('asset', 'UNKNOWN'), prices_dict)
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        
        if live_p is not None and entry_p > 0:
            # P/L logic: (live - entry) / entry * wager
            pnl = wager * ((live_p - entry_p) / entry_p)
            unreal_total += pnl
            open_trades.at[idx, 'profit_usd'] = pnl
    return float(unreal_total), open_trades

def format_institutional_ledger(df, prices_dict):
    """Formats the data for the Dashboard view."""
    if df is None or df.empty: return pd.DataFrame()
    report = []
    now = datetime.now().replace(tzinfo=None)
    
    df['status_check'] = df['result_clean'].astype(str).str.lower().str.strip()
    
    for _, row in df.iterrows():
        asset_name = str(row.get('asset', '???')).strip().upper()
        res_clean = row.get('status_check', 'unknown')
        entry_p = float(row.get('price', 0))
        wager = float(row.get('wager', 0))
        peak_p = float(row.get('result', entry_p)) 
        
        if res_clean == 'open':
            status = "🟢 ACTIVE"
            live_p = get_live_price(asset_name, prices_dict)
            mtm = float(live_p) if live_p is not None else entry_p
            # Return as %
            ret_pct = ((mtm - entry_p) / entry_p) * 100 if entry_p > 0 else 0
            pnl_val = wager * (ret_pct / 100)
        else:
            status = "✅ CLOSED"
            ret_pct = float(row.get('profit_usd', 0)) # Jace stores percentage in profit_usd for closed trades
            pnl_val = wager * (ret_pct / 100)
            # MTM is exit price
            mtm = float(row.get('result', entry_p)) 
            
        try:
            ts = pd.to_datetime(row.get('timestamp')).tz_localize(None)
            diff = now - ts
            age_str = f"{diff.days}d {diff.seconds // 3600}h"
        except: age_str = "---"

        report.append({
            "Ticker": asset_name, 
            "Status": status, 
            "Age": age_str,
            "Entry Price": entry_p,
            "Peak Price": peak_p,
            "MTM Price": mtm,
            "Return (%)": ret_pct, 
            "P/L ($)": pnl_val
        })
    return pd.DataFrame(report)
