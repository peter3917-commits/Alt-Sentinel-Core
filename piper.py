import pandas as pd
import os
import streamlit as st
from datetime import datetime

# --- ALT-SENTINEL FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20
# 🛡️ BRIAN_ALLOCATION REMOVED: Calculation below now reflects unified balance.

def get_firm_ledger(conn, prices_dict=None):
    """
    Piper: The High-Precision Accountant.
    Unified Balance Model: No hidden reserves or hardcoded subtractions.
    """
    default_data = {
        "vault_cash": INITIAL_CAPITAL, 
        "tradable_balance": INITIAL_CAPITAL, 
        "tax_pot": 0.0, 
        "burn": 0.0, 
        "trades_df": pd.DataFrame()
    }
    
    try:
        # STEP 1: Fresh Ledger Fetch (Forced TTL=0 to bypass the £200 ghost cache)
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
        
        # Labels that signify a trade is no longer taking up "Tradable Balance"
        win_labels = ['win', 'win_moonshot', 'win_trailing', 'trail_exit', 'closed', 'grid_harvest']
        
        # 1. Calculate Realized P/L (Sums all 'profit_usd' from finished trades)
        realized = float(df[df['status_check'].isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # 2. Calculate Overheads (Burn)
        burn = 0.0
        if os.path.exists('overheads.csv'):
            try:
                overhead_df = pd.read_csv('overheads.csv')
                burn = float(pd.to_numeric(overhead_df['amount'], errors='coerce').abs().sum())
            except: 
                burn = 0.0

        # 3. Tax Reserve (20% of the sum of profits from winning labels)
        winning_profit = float(df[df['status_check'].isin(win_labels)]['profit_usd'].sum())
        tax_pot = winning_profit * PROFIT_TAX_PCT
        if tax_pot < 0: 
            tax_pot = 0.0 
        
        # 4. Vault Cash (Seed + Profit - Expenses)
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # 5. Locked Wagers (ONLY subtracts wagers where status is 'open')
        # This is where the £200 usually hides if a row isn't marked 'closed'
        locked_wagers = float(df[df['status_check'] == 'open']['wager'].sum())

        # --- 🎯 THE UNIFIED CALCULATION ---
        # We NO LONGER subtract BRIAN_ALLOCATION.
        tradable_balance = float(vault_cash - tax_pot - locked_wagers)

        return {
            "vault_cash": vault_cash,
            "tradable_balance": tradable_balance,
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
