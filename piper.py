import pandas as pd
import os
from datetime import datetime

# --- ALT-SENTINEL FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20
BRIAN_ALLOCATION = 200.00  # 🛡️ THE SURVIVAL SHIELD: 20% reserved for Grid Harvester

def get_firm_ledger(conn, prices_dict=None):
    """
    Piper: The High-Precision Accountant.
    Updated to protect Brian's £200.00 allocation and handle Grid tracking.
    """
    default_data = {
        "vault_cash": INITIAL_CAPITAL, 
        "tradable_balance": INITIAL_CAPITAL - BRIAN_ALLOCATION, 
        "tax_pot": 0.0, 
        "burn": 0.0, 
        "trades_df": pd.DataFrame()
    }
    
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
        df['status_check'] = df['result_clean'].astype(str).str.lower().str.strip()
        win_labels = ['win', 'win_moonshot', 'win_trailing', 'trail_exit', 'closed', 'grid_harvest']
        
        # Calculate Realized P/L (Including Brian's 'grid_harvest' labels)
        realized = float(df[df['status_check'].isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # Calculate Overheads (Burn)
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(pd.to_numeric(overhead_df['amount'], errors='coerce').abs().sum())
            except: burn = 0.0

        # Tax Reserve calculation (Piper takes 20% of every win, including Brian's)
        tax_pot = float(df[df['status_check'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT)
        if tax_pot < 0: tax_pot = 0.0 
        
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # Deduct wagers for currently OPEN trades
        locked_wagers = float(df[df['status_check'] == 'open']['wager'].sum())

        return {
            "vault_cash": vault_cash,
            "tradable_balance": float(vault_cash - tax_pot - locked_wagers - BRIAN_ALLOCATION),
            "tax_pot": tax_pot, 
            "burn": burn, 
            "trades_df": df
        }
    except Exception as e:
        print(f"🏛️ PIPER CRITICAL LEDGER ERROR: {e}")
        return default_data

# ... [rest of the get_live_price, calculate_unrealized, and format_institutional_ledger functions remain exactly as you provided]
