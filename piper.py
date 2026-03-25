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
    Optimized: Enhanced 'Burn' sanitation and balance tracking.
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
        
        if df is None or df.empty:
            return default_data

        # Clean column names
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        # Ensure numeric columns are floats
        numeric_cols = ['profit_usd', 'wager', 'price', 'result']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # --- THE STATUS CHECK BRIDGE ---
        # Handles potential missing 'result_clean' column
        status_col = 'result_clean' if 'result_clean' in df.columns else 'status'
        if status_col in df.columns:
            df['status_check'] = df[status_col].astype(str).str.lower().str.strip()
        else:
            df['status_check'] = 'unknown'

        win_labels = ['win', 'win_moonshot', 'win_trailing', 'trail_exit', 'closed', 'grid_harvest']
        
        # 1. Calculate Realized P/L
        realized = float(df[df['status_check'].isin(win_labels + ['loss', 'legacy_cleanup'])]['profit_usd'].sum())
        
        # 2. Calculate Overheads (Burn)
        burn = 0.0
        try:
            overhead_df = conn.read(worksheet="Overheads", ttl=0)
            if overhead_df is not None and not overhead_df.empty:
                overhead_df.columns = [str(c).lower().strip() for c in overhead_df.columns]
                if 'amount' in overhead_df.columns:
                    clean_amounts = overhead_df['amount'].astype(str).str.replace(r'[£$,]', '', regex=True)
                    burn = float(pd.to_numeric(clean_amounts, errors='coerce').abs().sum())
        except:
            burn = 0.0

        # 3. Tax Reserve (20% of winning profits)
        winning_profit = float(df[df['status_check'].isin(win_labels)]['profit_usd'].sum())
        tax_pot = max(0.0, winning_profit * PROFIT_TAX_PCT)
        
        # 4. Vault Cash (Initial + Realized Profit - Burn)
        vault_cash = float(INITIAL_CAPITAL + realized - burn)
        
        # 5. Locked Wagers (Active trades)
        locked_wagers = 0.0
        if 'wager' in df.columns:
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

def show_performance_metrics(ledger_data):
    """
    REQUIRED BY MAIN.PY: Renders the institutional dashboard metrics.
    """
    if not ledger_data or "trades_df" not in ledger_data:
        st.info("Awaiting ledger initialization...")
        return

    # Extract data from dictionary
    df = ledger_data["trades_df"]
    vault = ledger_data["vault_cash"]
    tradable = ledger_data["tradable_balance"]
    burn = ledger_data["burn"]
    tax = ledger_data["tax_pot"]

    # UI Header Metrics
    st.subheader("🏛️ Institutional Capital Overview")
    m1, m2, m3, m4 = st.columns(4)
    
    m1.metric("Vault Cash", f"${vault:,.2f}", help="Initial + Realized P/L - Overheads")
    m2.metric("Tradable Power", f"${tradable:,.2f}", delta=f"{((tradable/INITIAL_CAPITAL)-1)*100:.1f}%")
    m3.metric("Tax Reserve", f"${tax:,.2f}", delta_color="inverse")
    m4.metric("Operational Burn", f"${burn:,.2f}", delta_color="inverse")

    if not df.empty:
        st.divider()
        st.subheader("📜 Master Audit Log")
        
        # Clean the display for the desk
        display_df = df.copy()
        if 'timestamp' in display_df.columns:
            display_df = display_df.sort_values('timestamp', ascending=False)
            
        st.dataframe(display_df, use_container_width=True, hide_index=True)

def format_institutional_ledger(df, params=None):
    if df.empty:
        return df
    display_df = df.copy()
    display_df.columns = [str(c).replace('_', ' ').title() for c in display_df.columns]
    if 'Timestamp' in display_df.columns:
        display_df = display_df.sort_values('Timestamp', ascending=False)
    return display_df
