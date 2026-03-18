import pandas as pd
import os
import streamlit as st
from datetime import datetime

# --- ALT-SENTINEL FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20
# 🛡️ THE SURVIVAL SHIELD IS REMOVED: Brian now uses 2% Dynamic Risk from the main pool.

def get_firm_ledger(conn, prices_dict=None):
    """
    Piper: The High-Precision Accountant.
    Updated: Unified Balance Model. Brian's £200 is released back to Tradable Balance.
    """
    default_data = {
        "vault_cash": INITIAL_CAPITAL, 
        "tradable_balance": INITIAL_CAPITAL, 
        "tax_pot": 0.0, 
        "burn": 0.0, 
        "trades_df": pd.DataFrame()
    }
    
    try:
        # STEP 1: Fresh Ledger Fetch
        df = conn.read(worksheet="Ledger", ttl=0)
        
        if df.empty:
            return default_data

        # Clean column names
        df.columns = [c.lower().strip() for c in df.columns]
        
        # Ensure numeric columns are floats
        numeric_cols = ['profit_usd', 'wager', 'price', 'result']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # --- THE PEAK TRACKING FIX ---
        df['status_check'] = df['result_clean'].astype(str).str.lower().str.strip()
        
        # Updated Labels: Jace uses 'closed', Brian uses 'closed' or 'grid_harvest'
        win_labels = ['win', 'win_moonshot', 'win_trailing', 'trail_exit', 'closed', 'grid_harvest']
        
        # Calculate Realized P/L
        realized = float(df[df['status_check'].isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # Calculate Overheads (Burn)
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(pd.to_numeric(overhead_df['amount'], errors='coerce').abs().sum())
            except: 
                burn = 0.0

        # Tax Reserve (Piper takes 20% of all closed winning trades)
        tax_pot = float(df[df['status_check'].isin(win_labels)]['profit_usd'].sum() * PROFIT_TAX_PCT)
        if tax_pot < 0: 
            tax_pot = 0.0 
        
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # Deduct wagers for currently OPEN trades (Jace's buys and Brian's Grid Buys)
        locked_wagers = float(df[df['status_check'] == 'open']['wager'].sum())

        return {
            "vault_cash": vault_cash,
            # 🚀 NEW: Tradable Balance now includes the £200 previously held by Brian
            "tradable_balance": float(vault_cash - tax_pot - locked_wagers),
            "tax_pot": tax_pot, 
            "burn": burn, 
            "trades_df": df
        }
    except Exception as e:
        st.error(f"🏛️ PIPER CRITICAL LEDGER ERROR: {e}")
        return default_data

def format_institutional_ledger(df, params=None):
    if df.empty:
        return df
    display_df = df.copy()
    display_df.columns = [str(c).replace('_', ' ').title() for c in display_df.columns]
    if 'Timestamp' in display_df.columns:
        display_df = display_df.sort_values('Timestamp', ascending=False)
    return display_df
