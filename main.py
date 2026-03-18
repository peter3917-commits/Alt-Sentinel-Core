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

# --- ⚡ CACHING ENGINE ---
@st.cache_data(ttl=60)
def fetch_vault_data(_conn):
    try:
        return _conn.read(worksheet="Vault", ttl=0)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_ledger_data(_conn):
    return piper.get_firm_ledger(_conn)

# --- 🏛️ THE FIRM HEADQUARTERS ---
conn = st.connection("gsheets", type=GSheetsConnection)
raw_vault = fetch_vault_data(conn)

# --- 🛡️ GLOBAL DATA HARDENING (REPAIRED) ---
vault_df = pd.DataFrame()
bal_col = 'price_usd' # Default

if not raw_vault.empty:
    vault_df = raw_vault.copy()
    # Normalize headers
    vault_df.columns = [str(c).lower().strip() for c in vault_df.columns]
    
    # Identify price column (check for common variants)
    for col in ['price_usd', 'balance', 'price', 'value']:
        if col in vault_df.columns:
            bal_col = col
            break
            
    if 'asset' in vault_df.columns:
        vault_df['asset'] = vault_df['asset'].astype(str).str.upper().str.strip()
    
    # Force numeric and datetime
    vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
    vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
    
    if vault_df['timestamp'].dt.tz is not None:
        vault_df['timestamp'] = vault_df['timestamp'].dt.tz_localize(None)
    
    # Only drop rows if they are truly unusable
    vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

tab1, tab2, tab3 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office", "🚜 The Harvester"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Alt-Sentinel: High-Precision Desk")
    
    if st.sidebar.button("🔄 Force Clear Cache"):
        st.cache_data.clear()
        st.rerun()

    try:
        ledger_data = fetch_ledger_data(conn)
        live_ledger_df = ledger_data['trades_df']
        
        # --- ASSET LOOP ---
        for coin in ASSETS:
            price = vance.scout_live_price(coin)
            
            with st.container():
                st.divider()
                st.header(f"🛰️ Sector: {coin}")
                
                if price:
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Live {coin}", f"${price:,.6f}")
                    
                    # Get history for this coin
                    asset_history = pd.DataFrame()
                    if not vault_df.empty and 'asset' in vault_df.columns:
                        asset_history = vault_df[vault_df['asset'] == coin.upper()].copy()

                    if not asset_history.empty:
                        # Kael's Analysis
                        analysis = kael.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                        if analysis and analysis[0] is not None:
                            moving_avg, snap_pct, rsi_val, hook_found = analysis
                            c2.metric("Avg Window", f"${moving_avg:,.6f}")
                            st_color = "normal" if snap_pct > 0 else "inverse"
                            c3.metric("Snap %", f"{snap_pct:.3f}%", delta=f"{snap_pct:.3f}%", delta_color=st_color)
                            c4.metric("RSI (100)", f"{rsi_val:.1f}")
                            
                            # Charting
                            chart_df = asset_history.tail(100).rename(columns={bal_col: 'Price'})
                            line_chart = alt.Chart(chart_df).mark_line(color="#00ff00" if snap_pct > 0 else "#ff4b4b").encode(
                                x='timestamp:T',
                                y=alt.Y('Price:Q', scale=alt.Scale(zero=False))
                            ).properties(height=200).interactive()
                            st.altair_chart(line_chart, width="stretch")
                            
                            # Jace executes
                            jace.execute_trade(coin, price, moving_avg, rsi_val, hook_found, live_ledger_df)
                    else:
                        st.info(f"📡 Waiting for historical data for {coin}...")
                else:
                    st.error(f"❌ Vance could not reach the {coin} scout.")

    except Exception as e:
        st.error(f"Sentinel System Error: {e}")

# (Tabs 2 and 3 remain the same as previous stable version)
