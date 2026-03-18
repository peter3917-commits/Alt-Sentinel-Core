import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import vance, kael, jace, piper, brian
from datetime import datetime, timedelta
import altair as alt

st.set_page_config(page_title="Alt-Sentinel: High-Precision Desk", page_icon="🏛️", layout="wide")

# --- 🛰️ ASSET CONFIGURATION ---
ASSETS = ["XRP", "XLM", "HBAR"]

# --- ⚡ CACHING ENGINE ---
@st.cache_data(ttl=60)
def fetch_vault_data(_conn):
    # Removing row limits to ensure all 1,600+ records are pulled
    df = _conn.read(worksheet="Vault", ttl=0)
    return df

@st.cache_data(ttl=60)
def fetch_ledger_data(_conn):
    return piper.get_firm_ledger(_conn)

# --- 🏛️ GLOBAL DATA INITIALIZATION ---
conn = st.connection("gsheets", type=GSheetsConnection)
raw_vault = fetch_vault_data(conn)
ledger_data = fetch_ledger_data(conn) # Fetch once for all tabs

# --- 🛡️ DATA HARDENING ---
vault_df = pd.DataFrame()
bal_col = 'price_usd'

if not raw_vault.empty:
    vault_df = raw_vault.copy()
    vault_df.columns = [str(c).lower().strip() for c in vault_df.columns]
    
    # Identify price column
    for c in ['price_usd', 'balance', 'price']:
        if c in vault_df.columns:
            bal_col = c
            break

    # Format and Sort
    vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
    vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
    vault_df = vault_df.dropna(subset=['timestamp', bal_col])
    # IMPORTANT: Sort by time so graphs connect properly
    vault_df = vault_df.sort_values('timestamp', ascending=True)

# --- 📱 UI LAYOUT ---
tab1, tab2, tab3 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office", "🚜 The Harvester"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Alt-Sentinel: High-Precision Desk")
    st.sidebar.write(f"📊 Total Records Loaded: {len(vault_df)}")
    
    if not vault_df.empty:
        for coin in ASSETS:
            price = vance.scout_live_price(coin)
            if price:
                # Filter for specific coin
                coin_history = vault_df[vault_df['asset'].str.upper() == coin.upper()].copy()
                
                with st.container():
                    st.divider()
                    st.header(f"🛰️ Sector: {coin}")
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Live Price", f"${price:,.6f}")
                    
                    if not coin_history.empty:
                        # Kael's Analysis
                        analysis = kael.check_for_snap(coin, price, coin_history.rename(columns={bal_col: "price_usd"}))
                        if analysis and analysis[0] is not None:
                            ma, snap, rsi, hook = analysis
                            c2.metric("Moving Avg", f"${ma:,.6f}")
                            c3.metric("Snap %", f"{snap:.3f}%")
                            c4.metric("RSI", f"{rsi:.1f}")
                        
                        # --- 📈 THE GRAPH FIX ---
                        # We take the last 300 points but ensured they are sorted by time
                        chart_data = coin_history.tail(300).rename(columns={bal_col: 'Price'})
                        
                        line = alt.Chart(chart_df if 'chart_df' in locals() else chart_data).mark_line(
                            color="#00ff00" if snap > 0 else "#ff4b4b"
                        ).encode(
                            x=alt.X('timestamp:T', title='Time (Last 300 Samples)'),
                            y=alt.Y('Price:Q', scale=alt.Scale(zero=False)),
                            tooltip=['timestamp', 'Price']
                        ).properties(height=300).interactive()
                        
                        st.altair_chart(line, width="stretch")

# --- 🧾 TAB 2: ACCOUNTING (PIPER) ---
with tab2:
    st.title("💼 Accounting Office")
    if ledger_data:
        m1, m2, m3 = st.columns(3)
        m1.metric("Vault Cash", f"£{ledger_data['vault_cash']:,.2f}")
        m2.metric("Tax Pot", f"£{ledger_data['tax_pot']:,.2f}")
        m3.metric("Burn", f"£{ledger_data['burn']:,.2f}")
        st.dataframe(piper.format_institutional_ledger(ledger_data['trades_df'], {}), width="stretch")

# --- 🚜 TAB 3: THE HARVESTER (BRIAN) ---
with tab3:
    st.title("🚜 The Harvester")
    target = st.selectbox("Harvest Sector", ASSETS, index=2)
    b_price = vance.scout_live_price(target)
    
    if b_price:
        harvester = brian.BrianHarvester(anchor_price=b_price)
        st.write(f"Grid active at: ${b_price:,.6f}")
        st.dataframe(harvester.active_grid, width="stretch")
