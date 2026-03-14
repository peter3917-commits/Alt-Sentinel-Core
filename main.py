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
        
        # 1. FETCH VAULT (Sheet 1)
        vault_df = conn.read(worksheet="Vault", ttl=0)
        
        # 2. FETCH LEDGER (Sheet 2)
        ledger_data = piper.get_firm_ledger(conn)
        live_ledger_df = ledger_data['trades_df']

        # --- SYSTEM HEARTBEAT (Sidebar Debug) ---
        st.sidebar.divider()
        st.sidebar.subheader("📡 System Heartbeat")
        st.sidebar.write(f"Vault Rows: {len(vault_df)}")
        st.sidebar.write(f"Ledger Rows: {len(live_ledger_df)}")

        if not vault_df.empty:
            vault_df.columns = [c.lower().strip() for c in vault_df.columns]
            bal_col = 'balance' if 'balance' in vault_df.columns else 'price_usd'
            vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
            vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce').dt.tz_localize(None)
            vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

            for coin in ASSETS:
                with st.container():
                    price = vance.scout_live_price(coin)
                    if price:
                        st.divider()
                        st.header(f"🛰️ Sector: {coin}")
                        
                        # Filter history for the last 72h
                        asset_history = vault_df[vault_df['asset'].str.upper() == coin.upper()].copy()
                        cutoff = datetime.now() - timedelta(hours=72)
                        asset_history = asset_history[asset_history['timestamp'] > cutoff]
                        
                        if asset_history.empty:
                            st.warning(f"⚠️ No recent data in Vault for {coin}. Check Scout_job.")
                            continue

                        c1, c2, c3, c4 = st.columns(4)
                        c1.metric(f"Live {coin}", f"${price:,.6f}")
                        
                        # 🏛️ KAEL: ANALYZE
                        analysis = kael.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                        if analysis and analysis[0] is not None:
                            moving_avg, snap_pct, rsi_val, hook_found = analysis
                            c2.metric("Avg Window", f"${moving_avg:,.6f}")
                            st_color = "normal" if snap_pct > 0 else "inverse"
                            c3.metric("Snap %", f"{snap_pct:.3f}%", delta=f"{snap_pct:.3f}%", delta_color=st_color)
                            c4.metric("RSI (100)", f"{rsi_val:.1f}")
                            
                            # --- 📈 24H CHART (Fixed Syntax) ---
                            chart_cutoff = datetime.now() - timedelta(hours=24)
                            chart_data = asset_history[asset_history['timestamp'] > chart_cutoff].copy()

                            if not chart_data.empty:
                                chart_df = chart_data[['timestamp', bal_col]].rename(columns={bal_col: 'Price'})
                                line_chart = alt.Chart(chart_df).mark_line(
                                    color="#00ff00" if snap_pct > 0 else "#ff4b4b", strokeWidth=2
                                ).encode(
                                    x=alt.X('timestamp:T', title='Timeline'),
                                    y=alt.Y('Price:Q', title='Price ($)', scale=alt.Scale(zero=False)),
                                    tooltip=['timestamp', alt.Tooltip('Price:Q', format=',.6f')]
                                ).properties(height=200).interactive()
                                
                                st.altair_chart(line_chart, width="stretch")
                            
                            # 🏛️ JACE: EXECUTE
                            outcome, action_data = jace.execute_trade(coin, price, moving_avg, rsi_val, hook_found, live_ledger_df)
                            
                            # Update Logic (BUY/CLOSE/PEAK)
                            if outcome == "BUY" and action_data:
                                cols = ['timestamp', 'asset', 'type', 'price', 'wager', 'result', 'profit_usd', 'result_clean']
                                new_row = pd.DataFrame([action_data], columns=cols)
                                updated_df = pd.concat([live_ledger_df, new_row], ignore_index=True)
                                conn.update(worksheet="Ledger", data=updated_df)
                                st.success(f"🚀 POSITION OPENED: {coin}")
                                st.rerun()
                            
                            elif outcome == "CLOSE" and action_data:
                                idx = action_data['index']
                                live_ledger_df.at[idx, 'result_clean'] = "CLOSED"
                                live_ledger_df.at[idx, 'profit_usd'] = action_data['profit_usd']
                                live_ledger_df.at[idx, 'result'] = action_data.get('price', price)
                                conn.update(worksheet="Ledger", data=live_ledger_df)
                                st.warning(f"🎯 CLOSED: {coin}")
                                st.rerun()

                            elif outcome == "PEAK_UPDATE" and action_data:
                                idx = action_data['index']
                                live_ledger_df.at[idx, 'result'] = action_data['new_peak']
                                conn.update(worksheet="Ledger", data=live_ledger_df)
                                st.toast(f"📈 {coin} Peak: ${action_data['new_peak']:.6f}")

                            st.caption(f"Status: {outcome}")

        else:
            st.error("Vault sheet is empty. Please run Scout_job to populate data.")

    except Exception as e:
        st.error(f"Sentinel System Error: {e}")

# --- 🧾 TAB 2: ACCOUNTING (Fixed Syntax) ---
with tab2:
    st.title("💼 Executive Summary")
    try:
        ledger = piper.get_firm_ledger(conn)
        if not ledger['trades_df'].empty:
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            # Logic for Tab 2 metrics remains the same
            st.divider()
            desk_df = piper.format_institutional_ledger(ledger['trades_df'], {})
            st.dataframe(desk_df, width="stretch", height=450)
    except Exception as e:
        st.error(f"Accountant Error: {e}")
