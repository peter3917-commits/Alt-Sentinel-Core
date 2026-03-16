import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import vance, kael, jace, piper  # AGENT IDENTITIES
from datetime import datetime, timedelta
import altair as alt

# --- ALT-SENTINEL INSTITUTIONAL LAYOUT ---
st.set_page_config(page_title="Alt-Sentinel: High-Precision Desk", page_icon="🏛️", layout="wide")

# --- 🛰️ ASSET CONFIGURATION ---
ASSETS = ["XRP", "XLM", "HBAR"]

# --- ⚡ CACHING ENGINE (Hardened for 2026 Health Checks) ---
@st.cache_data(ttl=60)
def fetch_vault_data(_conn):
    try:
        return _conn.read(worksheet="Vault", ttl=0)
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_ledger_data(_conn):
    return piper.get_firm_ledger(_conn)

# --- 🏛️ THE FIRM HEADQUARTERS ---
tab1, tab2 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Alt-Sentinel: High-Precision Desk")
    
    # Move Sidebar elements into a stable container to prevent boot-hang
    with st.sidebar:
        st.header("⚙️ Desk Controls")
        auto_trade = st.toggle("Activate Vance Auto-Scout", value=False)
        if auto_trade:
            st_autorefresh(interval=300000, key="vance_heartbeat")
            st.success("Vance is scouting...")

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        vault_df = fetch_vault_data(conn)
        ledger_data = fetch_ledger_data(conn)
        live_ledger_df = ledger_data['trades_df']
        live_ledger_df['Tradable_Balance'] = ledger_data['tradable_balance']

        # --- DATA HARDENING ---
        if not vault_df.empty:
            vault_df.columns = [str(c).lower().strip() for c in vault_df.columns]
            # Precise HBAR recovery logic
            bal_col = 'price_usd' if 'price_usd' in vault_df.columns else 'balance'
            
            vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
            vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
            if vault_df['timestamp'].dt.tz is not None:
                vault_df['timestamp'] = vault_df['timestamp'].dt.tz_localize(None)
            vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

        if not live_ledger_df.empty:
            live_ledger_df.columns = [str(c).lower().strip() for c in live_ledger_df.columns]

        # --- SYSTEM HEARTBEAT (Sidebar) ---
        st.sidebar.divider()
        st.sidebar.subheader("📡 System Heartbeat")
        st.sidebar.write(f"Vault Records: {len(vault_df)}")
        st.sidebar.write(f"Ledger Records: {len(live_ledger_df)}")

        # --- STAFF POLICY (2026 Deprecation Fix) ---
        with st.sidebar.expander("📋 Active Staff Policy", expanded=False):
            policy_data = {
                "Agent": ["Jace", "Jace", "Jace", "Kael"],
                "Param": ["Stop", "Profit", "Trail", "RSI"],
                "Val": ["-3.5%", "2.0%", "10.0%", "100"]
            }
            st.dataframe(pd.DataFrame(policy_data), width="stretch", hide_index=True)

        # --- ASSET LOOP ---
        if not vault_df.empty:
            for coin in ASSETS:
                price = vance.scout_live_price(coin)
                if price:
                    asset_history = vault_df[vault_df['asset'].str.upper() == coin.upper()].copy()
                    cutoff = datetime.now() - timedelta(hours=72)
                    asset_history = asset_history[asset_history['timestamp'] > cutoff]
                    
                    if asset_history.empty:
                        st.warning(f"📡 {coin}: Data sync pending...")
                        continue

                    # --- SIDEBAR INTEL ---
                    active_trade = live_ledger_df[(live_ledger_df['asset'].str.upper() == coin.upper()) & 
                                                 (live_ledger_df['result_clean'].str.upper() == 'OPEN')]
                    
                    if not active_trade.empty:
                        entry = float(active_trade.iloc[-1]['price'])
                        peak = float(active_trade.iloc[-1]['result'])
                        with st.sidebar.expander(f"🟢 {coin} Intel", expanded=True):
                            st.caption(f"🛡️ Stop: `${(entry * 0.965):,.6f}`")
                            st.caption(f"📈 Trail: `${(peak * 0.90):,.6f}`")

                    # --- MAIN DISPLAY ---
                    with st.container():
                        st.divider()
                        st.header(f"🛰️ Sector: {coin}")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(f"Live {coin}", f"${price:,.6f}")
                        
                        analysis = kael.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                        if analysis and analysis[0] is not None:
                            moving_avg, snap_pct, rsi_val, hook_found = analysis
                            c2.metric("Avg Window", f"${moving_avg:,.6f}")
                            c3.metric("Snap %", f"{snap_pct:.3f}%", delta=f"{snap_pct:.3f}%")
                            c4.metric("RSI (100)", f"{rsi_val:.1f}")
                            
                            # --- 📈 CHART (2026 width="stretch") ---
                            chart_df = asset_history.tail(288)[['timestamp', bal_col]].rename(columns={bal_col: 'Price'})
                            line_chart = alt.Chart(chart_df).mark_line(color="#00ff00").encode(
                                x=alt.X('timestamp:T'),
                                y=alt.Y('Price:Q', scale=alt.Scale(zero=False))
                            ).properties(height=200).interactive()
                            st.altair_chart(line_chart, width="stretch")
                            
                            # --- EXECUTION ENGINE ---
                            outcome, action_data = jace.execute_trade(coin, price, moving_avg, rsi_val, hook_found, live_ledger_df)
                            if outcome in ["BUY", "CLOSE", "PEAK_UPDATE"]:
                                st.cache_data.clear()
                                st.rerun()
        else:
            st.error("Vault data is currently inaccessible.")

    except Exception as e:
        st.error(f"Sentinel System Error: {e}")

# --- 🧾 TAB 2: ACCOUNTING ---
with tab2:
    st.title("💼 Executive Summary")
    try:
        ledger = fetch_ledger_data(conn)
        if not ledger['trades_df'].empty:
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vault Cash", f"£{ledger['vault_cash']:,.2f}")
            m2.metric("Tradable Balance", f"£{ledger['tradable_balance']:,.2f}")
            m3.metric("Tax Pot", f"£{ledger['tax_pot']:,.2f}")
            m4.metric("Burn (Overheads)", f"£{ledger['burn']:,.2f}")
            
            st.divider()
            desk_df = piper.format_institutional_ledger(ledger['trades_df'], {})
            st.dataframe(desk_df, width="stretch", height=450)
    except Exception as e:
        st.error(f"Accountant Error: {e}")
