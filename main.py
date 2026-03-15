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

# --- ⚡ CACHING ENGINE (Fixes the "Vanishing" Bug) ---
# Holds data in memory for 15s to prevent intermittent UI flickering
@st.cache_data(ttl=15)
def fetch_vault_data(_conn):
    return _conn.read(worksheet="Vault", ttl=0)

@st.cache_data(ttl=15)
def fetch_ledger_data(_conn):
    return piper.get_firm_ledger(_conn)

# --- 🏛️ THE FIRM HEADQUARTERS ---
tab1, tab2 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Alt-Sentinel: High-Precision Desk")
    
    auto_trade = st.sidebar.toggle("Activate Vance Auto-Scout", value=False)
    if auto_trade:
        st_autorefresh(interval=300000, key="vance_heartbeat")
        st.sidebar.success("Vance is scouting the Alt-Sectors...")

    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # 1. FETCH PROTECTED DATA
        vault_df = fetch_vault_data(conn)
        ledger_data = fetch_ledger_data(conn)
        live_ledger_df = ledger_data['trades_df']
        
        # 🟢 COMPOUND ENGINE: Inject Tradable Balance for Jace's 20% wager calculation
        live_ledger_df['Tradable_Balance'] = ledger_data['tradable_balance']

        # --- DATA HARDENING (Preserved precisely from your original) ---
        if not vault_df.empty:
            vault_df.columns = [str(c).lower().strip() for c in vault_df.columns]
            bal_col = 'price_usd' if 'price_usd' in vault_df.columns else 'balance'
            
            vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
            vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
            
            if vault_df['timestamp'].dt.tz is not None:
                vault_df['timestamp'] = vault_df['timestamp'].dt.tz_localize(None)
            
            vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

        if not live_ledger_df.empty:
            live_ledger_df.columns = [str(c).lower().strip() for c in live_ledger_df.columns]

        # --- SYSTEM HEARTBEAT ---
        st.sidebar.divider()
        st.sidebar.subheader("📡 System Heartbeat")
        st.sidebar.write(f"Vault Records: {len(vault_df)}")
        st.sidebar.write(f"Ledger Records: {len(live_ledger_df)}")

        # --- 🏛️ STAFF MANIFESTO (Transparency preserved) ---
        st.sidebar.divider()
        st.sidebar.subheader("📋 Active Staff Policy")
        with st.sidebar.expander("Live Execution Parameters", expanded=True):
            policy_data = {
                "Agent": ["Jace", "Jace", "Jace", "Jace", "Kael", "Kael"],
                "Parameter": ["Stop Loss", "Profit Target", "Trailing Stop", "Entry Snap", "MA Window", "RSI Period"],
                "Value": ["-3.5%", "2.0%", "10.0%", "-2.0%", "24h (288)", "100"]
            }
            st.table(pd.DataFrame(policy_data))

        # --- ASSET LOOP ---
        if not vault_df.empty:
            for coin in ASSETS:
                price = vance.scout_live_price(coin)
                if price:
                    asset_history = vault_df[vault_df['asset'].str.upper() == coin.upper()].copy()
                    cutoff = datetime.now() - timedelta(hours=72)
                    asset_history = asset_history[asset_history['timestamp'] > cutoff]
                    
                    if asset_history.empty:
                        st.warning(f"📡 {coin}: No data in last 72h. Check Scout_job.")
                        continue

                    # --- SIDEBAR INTEL (Protection logic preserved) ---
                    active_trade = live_ledger_df[(live_ledger_df['asset'].str.upper() == coin.upper()) & 
                                                 (live_ledger_df['result_clean'].str.upper() == 'OPEN')]
                    
                    if not active_trade.empty:
                        entry = float(active_trade.iloc[-1]['price'])
                        peak = float(active_trade.iloc[-1]['result'])
                        with st.sidebar.expander(f"🟢 {coin} Intel", expanded=True):
                            st.caption(f"🛡️ Stop: `${(entry * 0.965):,.6f}`")
                            st.caption(f"📈 Trail: `${(peak * 0.90):,.6f}`")
                            if price < (entry * 1.02):
                                st.info("🔒 Status: Dead Zone")

                    with st.container():
                        st.divider()
                        st.header(f"🛰️ Sector: {coin}")
                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(f"Live {coin}", f"${price:,.6f}")
                        
                        analysis = kael.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                        if analysis and analysis[0] is not None:
                            moving_avg, snap_pct, rsi_val, hook_found = analysis
                            c2.metric("Avg Window", f"${moving_avg:,.6f}")
                            st_color = "normal" if snap_pct > 0 else "inverse"
                            c3.metric("Snap %", f"{snap_pct:.3f}%", delta=f"{snap_pct:.3f}%", delta_color=st_color)
                            c4.metric("RSI (100)", f"{rsi_val:.1f}")
                            
                            # --- 📈 24H CHART (Fixed Width Warning) ---
                            chart_cutoff = datetime.now() - timedelta(hours=24)
                            chart_data = asset_history[asset_history['timestamp'] > chart_cutoff].copy()
                            if not chart_data.empty:
                                chart_df = chart_data[['timestamp', bal_col]].rename(columns={bal_col: 'Price'})
                                line_chart = alt.Chart(chart_df).mark_line(color="#00ff00" if snap_pct > 0 else "#ff4b4b").encode(
                                    x=alt.X('timestamp:T', title='Timeline'),
                                    y=alt.Y('Price:Q', title='Price ($)', scale=alt.Scale(zero=False)),
                                    tooltip=['timestamp', alt.Tooltip('Price:Q', format=',.6f')]
                                ).properties(height=200).interactive()
                                # DEPRECATION FIX: width="stretch"
                                st.altair_chart(line_chart, width="stretch")
                            
                            # --- 🏛️ JACE: EXECUTE ---
                            outcome, action_data = jace.execute_trade(coin, price, moving_avg, rsi_val, hook_found, live_ledger_df)
                            
                            if outcome == "BUY" and action_data:
                                updated_df = pd.concat([live_ledger_df, pd.DataFrame([action_data])], ignore_index=True)
                                conn.update(worksheet="Ledger", data=updated_df)
                                st.cache_data.clear()
                                st.rerun()
                            
                            elif outcome in ["CLOSE", "PEAK_UPDATE"] and action_data:
                                idx = action_data['index']
                                if outcome == "CLOSE":
                                    live_ledger_df.at[idx, 'result_clean'] = "CLOSED"
                                    live_ledger_df.at[idx, 'profit_usd'] = action_data['profit_usd']
                                else:
                                    live_ledger_df.at[idx, 'result'] = action_data['new_peak']
                                conn.update(worksheet="Ledger", data=live_ledger_df)
                                st.cache_data.clear()
                                st.rerun()
        else:
            st.error("Vault sheet is currently empty or unreadable.")

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
            # DEPRECATION FIX: width="stretch"
            st.dataframe(desk_df, width="stretch", height=450)
    except Exception as e:
        st.error(f"Accountant Error: {e}")
