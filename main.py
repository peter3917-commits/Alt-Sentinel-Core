import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import vance, kael, jace, piper, brian  # Your custom logic files
from datetime import datetime, timedelta
import altair as alt  # This is the real library for your charts

# --- ALT-SENTINEL INSTITUTIONAL LAYOUT ---
st.set_page_config(page_title="Alt-Sentinel: High-Precision Desk", page_icon="🏛️", layout="wide")

# --- 🛰️ ASSET CONFIGURATION ---
ASSETS = ["XRP", "XLM", "HBAR"]

# --- ⚡ THE DEEP-SYNC ENGINE ---
@st.cache_data(ttl=60)
def fetch_vault_data_direct():
    SHEET_ID = "15pD60KIjHB7GNEwlbsYg-STclQ0wKYOA7zkD5oYcaJQ"
    URL_VAULT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    URL_HARVESTER = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=2062418608"
    
    try:
        df_vault = pd.read_csv(URL_VAULT)
        try:
            df_harvest = pd.read_csv(URL_HARVESTER)
        except:
            df_harvest = pd.DataFrame()
        return df_vault, df_harvest
    except Exception as e:
        st.error(f"Vault Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_ledger_data(_conn):
    return piper.get_firm_ledger(_conn)

# --- 🏛️ GLOBAL DATA INITIALIZATION ---
conn = st.connection("gsheets", type=GSheetsConnection)
raw_vault, raw_harvester_log = fetch_vault_data_direct()
ledger_data = fetch_ledger_data(conn)

# --- 🛡️ DATA HARDENING (VAULT) ---
vault_df = pd.DataFrame()
bal_col = 'price_usd'

if not raw_vault.empty:
    vault_df = raw_vault.copy()
    vault_df.columns = [str(c).lower().strip() for c in vault_df.columns]
    
    if 'asset' not in vault_df.columns and len(vault_df.columns) >= 3:
        potential_asset_cols = [c for c in vault_df.columns if 'asset' in c or 'coin' in c]
        if potential_asset_cols:
            vault_df = vault_df.rename(columns={potential_asset_cols[0]: 'asset'})

    for c in ['price_usd', 'balance', 'price', 'balance2']:
        if c in vault_df.columns:
            bal_col = c
            break

    vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
    vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
    
    if 'asset' in vault_df.columns:
        vault_df['asset'] = vault_df['asset'].astype(str).str.upper().str.strip()

    vault_df = vault_df.dropna(subset=['timestamp', bal_col]).sort_values('timestamp', ascending=True)

# --- 📱 UI LAYOUT ---
tab1, tab2, tab3 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office", "🚜 The Harvester"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Alt-Sentinel: High-Precision Desk")
    st.sidebar.write(f"📊 Vault Records: {len(vault_df)}")
    
    auto_trade = st.sidebar.toggle("Activate Vance Auto-Scout", value=False)
    if auto_trade:
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
                            color="#00ff00" if ('snap' in locals() and snap > 0) else "#ff4b4b"
                        ).encode(
                            x=alt.X('timestamp:T', title='Timeline'),
                            y=alt.Y('Price:Q', scale=alt.Scale(zero=False)),
                            tooltip=['timestamp', alt.Tooltip('Price:Q', format=',.6f')]
                        ).properties(height=300).interactive()
                        st.altair_chart(line, use_container_width=True)
                        
                        if 'ma' in locals():
                            jace.execute_trade(coin, price, ma, rsi, hook, ledger_data['trades_df'])

# --- 🧾 TAB 2: ACCOUNTING ---
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
        st.dataframe(piper.format_institutional_ledger(ledger_data['trades_df'], {}), use_container_width=True)

# --- 🚜 TAB 3: THE HARVESTER ---
with tab3:
    st.title("🚜 The Harvester")
    target = st.selectbox("Harvest Sector", ASSETS, index=2)
    
    display_grid = pd.DataFrame()
    anchor = 0.0
    in_log = False

    if not raw_harvester_log.empty:
        raw_harvester_log.columns = [str(c).lower().strip() for c in raw_harvester_log.columns]
        current_log = raw_harvester_log[raw_harvester_log['sector'].astype(str).str.upper() == target.upper()]
        if not current_log.empty:
            display_grid = current_log
            anchor = float(current_log['anchor_price'].iloc[0])
            in_log = True

    if not in_log:
        if not vault_df.empty:
            latest_entry = vault_df[vault_df['asset'] == target.upper()].sort_values('timestamp').tail(1)
            
            if not latest_entry.empty:
                vault_price = float(latest_entry[bal_col].iloc[0])
                last_time = latest_entry['timestamp'].iloc[0]
                
                harvester = brian.BrianHarvester(anchor_price=vault_price)
                display_grid = harvester.active_grid
                anchor = vault_price
                
                st.info(f"📜 Vault True Price Found: **${anchor:,.6f}** (Logged: {last_time.strftime('%H:%M:%S')})")
                
                if st.button(f"🚀 Initialize {target} Grid from Vault"):
                    brian.save_to_log_with_memory(conn, harvester.active_grid, target, anchor)
                    st.success(f"Grid for {target} anchored to Vault Price!")
                    st.rerun()
            else:
                st.warning(f"⚠️ No price record for {target} found in the Vault yet.")
        else:
            st.error("🚨 Vault is empty. Wait for a heartbeat ping to establish price.")

    # --- DISPLAY METRICS ---
    c1, c2, c3 = st.columns(3)
    c1.metric("Reserved Budget", "£200.00")
    c2.metric("Grid Anchor", f"${anchor:,.6f}")
    c3.metric("Wager/Level", "£20.00")
    
    st.divider()
    st.subheader("📋 Active Harvest Orders")
    if not display_grid.empty:
        view_cols = ['level', 'type', 'price', 'status', 'wager_gbp']
        st.dataframe(display_grid[[c for c in view_cols if c in display_grid.columns]], hide_index=True, use_container_width=True)
    else:
        st.warning(f"No active grid for {target}. Ensure Vault data exists.")
    
    # --- 🛰️ UPDATED HARVESTER GRAPH WITH GRID OVERLAY ---
    if not vault_df.empty:
        b_hist = vault_df[vault_df['asset'] == target.upper()].tail(60).copy()
        if not b_hist.empty:
            st.subheader("📡 Live Geometric Escalator")
            b_hist = b_hist.rename(columns={bal_col: 'price'})
            
            # 1. Price Line
            price_line = alt.Chart(b_hist).mark_line(color="#1f77b4").encode(
                x=alt.X('timestamp:T', title='Time'),
                y=alt.Y('price:Q', title='Price (USD)', scale=alt.Scale(zero=False))
            )

            # 2. Grid Rungs Overlay (Using display_grid for levels)
            if not display_grid.empty:
                # Add color logic for the lines
                grid_viz = display_grid.copy()
                grid_viz['color'] = grid_viz['type'].apply(lambda x: '#228b22' if x == 'BUY' else '#d2322d')
                
                grid_rules = alt.Chart(grid_viz).mark_rule(
                    strokeDash=[5, 5], strokeWidth=1
                ).encode(
                    y='price:Q',
                    color=alt.Color('color:N', scale=None),
                    tooltip=['level', 'type', 'price']
                )
                
                # Combine
                final_chart = (price_line + grid_rules).properties(height=400).interactive()
            else:
                final_chart = price_line.properties(height=400).interactive()

            st.altair_chart(final_chart, use_container_width=True)
