import pandas as pd
import os
import streamlit as st
from datetime import datetime

# --- ALT-SENTINEL FINANCIAL SETTINGS ---
INITIAL_CAPITAL = 1000.00
PROFIT_TAX_PCT = 0.20

def get_firm_ledger(conn, prices_dict=None):
    """
    Piper: The High-Precision Accountant.
    Optimized: Enhanced 'Burn' sanitation to catch currency symbols and formatting.
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
        win_labels = ['win', 'win_moonshot', 'win_trailing', 'trail_exit', 'closed', 'grid_harvest']
        
        # 1. Calculate Realized P/L
        realized = float(df[df['status_check'].isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # 2. Calculate Overheads (Burn) from GSheets 🚀
        burn = 0.0
        try:
            overhead_df = conn.read(worksheet="Overheads", ttl=0)
            if not overhead_df.empty:
                # Force columns to lowercase and strip spaces
                overhead_df.columns = [str(c).lower().strip() for c in overhead_df.columns]
                
                if 'amount' in overhead_df.columns:
                    # 🛡️ SANITIZER: Removes symbols like £ or $ that stop math from working
                    clean_amounts = overhead_df['amount'].astype(str).str.replace(r'[£$,]', '', regex=True)
                    burn = float(pd.to_numeric(clean_amounts, errors='coerce').abs().sum())
        except Exception as e:
            burn = 0.0

        # 3. Tax Reserve (20% of winning profits)
        winning_profit = float(df[df['status_check'].isin(win_labels)]['profit_usd'].sum())
        tax_pot = winning_profit * PROFIT_TAX_PCT
        if tax_pot < 0: tax_pot = 0.0 
        
        # 4. Vault Cash (Initial + Realized Profit - Burn)
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # 5. Locked Wagers (Active trades)
        locked_wagers = float(df[df['status_check'] == 'open']['wager'].sum())

        # --- 🎯 THE UNIFIED CALCULATION ---
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
