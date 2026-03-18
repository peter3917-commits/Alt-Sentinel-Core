import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import vance, kael, jace, piper, brian
from datetime import datetime, timedelta
import altair as alt

# --- ALT-SENTINEL INSTITUTIONAL LAYOUT ---
st.set_page_config(page_title="Alt-Sentinel: High-Precision Desk", page_icon="🏛️", layout="wide")

# --- 🛰️ ASSET CONFIGURATION ---
ASSETS = ["XRP", "XLM", "HBAR"]

# --- ⚡ THE DEEP-SYNC ENGINE ---
@st.cache_data(ttl=60)
def fetch_vault_data_direct():
    SHEET_ID = "15pD60KIjHB7GNEwlbsYg-STclQ0wKYOA7zkD5oYcaJQ"
    URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    try:
        df = pd.read_csv(URL)
        return df
    except Exception as e:
        st.error(f"Vault Sync Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_ledger_data(_conn):
    return piper.get_firm_ledger(_conn)

# --- 🏛️ GLOBAL DATA INITIALIZATION ---
conn = st.connection("gsheets", type=GSheetsConnection)
raw_vault = fetch_vault_data_direct()
ledger_data = fetch_ledger_data(conn)

# --- 🛡️ DATA HARDENING (FIXES KEYERROR 'ASSET') ---
vault_df = pd.DataFrame()
bal_col = 'price_usd'

if not raw_vault.empty:
    vault_df = raw_vault.copy()
    
    # Force lowercase and remove hidden spaces from headers to prevent KeyError
    vault_df.columns = [str(c).lower().strip() for c in vault_df.columns]
    
    # CRITICAL FIX: Ensure 'asset' column exists even if sheet header is slightly off
    if 'asset' not in vault_df.columns and len(vault_df.columns) >= 3:
        # If your sheet is Staff, Timestamp, Asset, Price... Asset is index 2
        # If your sheet is Timestamp, Asset, Price... Asset is index 1
        # We search for it:
        potential_asset_cols = [c for c in vault_df.columns if 'asset' in c or 'coin' in c]
        if potential_asset_cols:
            vault_df = vault_df.rename(columns={potential_asset_cols[0]: 'asset'})

    # Identify price column
    for c in ['price_usd', 'balance', 'price', 'balance2']:
        if c in vault_df.columns:
            bal_col = c
            break

    # Format Data Types
    vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
    vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
    
    # Ensure 'asset' is string and uppercase for filtering
    if 'asset' in vault_df.columns:
        vault_df['asset'] = vault_df['asset'].astype(str).str.upper().str.strip()

    # Drop broken rows and sort
    vault_df = vault_df.dropna(subset=['timestamp', bal_col])
    vault_df = vault_df.sort_values('timestamp', ascending=True)

# --- 📱 UI LAYOUT ---
tab1, tab2, tab3 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office", "🚜 The Harvester"])

# --- 🛰️ TAB 1: SENTINEL ENGINE (Jace & Kael) ---
with tab1:
    st.title("🏛️ Alt-Sentinel: High-Precision Desk")
    st.sidebar.write(f"📊 Vault Records: {len(vault_df)}")
    
    auto_trade = st.sidebar.toggle("Activate Vance Auto-Scout", value=False)
    if auto_trade:
        # This triggers the 5-minute ping
        st_autorefresh(interval=300000, key="vance_heartbeat")

    if not vault_df.empty and 'asset' in vault_df.columns:
        for coin in ASSETS:
            price = vance.scout_live_price(coin)
            if price:
                coin_history = vault_df[vault_df['asset'] == coin.upper()].copy()
                
                with st.container():
                    st.divider()
                    st.header(f"🛰️ Sector: {coin}")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Live Price", f"${price:,.6f}")
                    
                    if not coin_history.empty:
                        analysis = kael.check_for_snap(coin, price, coin_history.rename(columns={bal_col: "price_usd"}))
                        if analysis and analysis[0] is not None:
                            ma, snap, rsi, hook = analysis
                            c2.metric("Moving Avg", f"${ma:,.6f}")
                            c3.metric("Snap %", f"{snap:.3f}%")
                            c4.metric("RSI", f"{rsi:.1f}")
                        
                        chart_data = coin_history.tail(300).rename(columns={bal_col: 'Price'})
                        line = alt.Chart(chart_data).mark_line(
                            color="#00ff00" if (not coin_history.empty and 'snap' in locals() and snap > 0) else "#ff4b4b"
                        ).encode(
                            x=alt.X('timestamp:T', title='Historical Timeline'),
                            y=alt.Y('Price:Q', scale=alt.Scale(zero=False)),
                            tooltip=['timestamp', alt.Tooltip('Price:Q', format=',.6f')]
                        ).properties(height=300).interactive()
                        
                        st.altair_chart(line, width="stretch")
                        
                        if 'ma' in locals():
                            jace.execute_trade(coin, price, ma, rsi, hook, ledger_data['trades_df'])

# --- 🧾 TAB 2: ACCOUNTING (PIPER) ---
with tab2:
    st.title("💼 Accounting Office")
    if ledger_data:
        st.subheader("📊 Operational Health")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Vault Cash", f"£{ledger_data['vault_cash']:,.2f}")
        m2.metric("Tradable Balance", f"£{ledger_data['tradable_balance']:,.2f}")
        m3.metric("Tax Pot", f"£{ledger_data['tax_pot']:,.2f}")
        m4.metric("Burn", f"£{ledger_data['burn']:,.2f}")
        st.divider()
        st.dataframe(piper.format_institutional_ledger(ledger_data['trades_df'], {}), width="stretch")

# --- 🚜 TAB 3: THE HARVESTER (BRIAN) ---
with tab3:
    st.title("🚜 The Harvester")
    target = st.selectbox("Harvest Sector", ASSETS, index=2)
    b_price = vance.scout_live_price(target)
    
    if b_price:
        harvester = brian.BrianHarvester(anchor_price=b_price)
        
        c1, c2, c3 = st.columns(3)
        c1.metric("Reserved Budget", "£200.00")
        c2.metric("Grid Anchor", f"${b_price:,.6f}")
        c3.metric("Wager/Level", "£20.00")
        
        st.divider()
        st.subheader("📋 Active Harvest Orders")
        st.dataframe(harvester.active_grid, width="stretch", hide_index=True)
        
        # FIXED CHART LOGIC:
        if not vault_df.empty and 'asset' in vault_df.columns:
            b_hist = vault_df[vault_df['asset'] == target.upper()].tail(60)
            if not b_hist.empty:
                st.subheader("📡 Live Geometric Escalator")
                b_chart = alt.Chart(b_hist.rename(columns={bal_col: 'price'})).mark_line(color="#8884d8").encode(
                    x='timestamp:T', 
                    y=alt.Y('price:Q', scale=alt.Scale(zero=False))
                )
                st.altair_chart(b_chart.properties(height=400), width="stretch")
            else:
                st.info(f"Waiting for more vault data for {target}...")
