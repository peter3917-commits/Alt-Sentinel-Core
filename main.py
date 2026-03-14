import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import vance, kael, jace, piper  # AGENT IDENTITIES
from datetime import datetime, timedelta
import altair as alt

# --- ALT-SENTINEL INSTITUTIONAL LAYOUT ---
st.set_page_config(page_title="Alt-Sentinel: High-Precision Desk", page_icon="🏛️", layout="wide")

# --- 🛰️ ASSET CONFIGURATION (High Precision Sector) ---
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
        
        # Fresh Ledger Fetch for Jace's awareness
        ledger_data = piper.get_firm_ledger(conn)
        live_ledger_df = ledger_data['trades_df']

        vault_df = conn.read(worksheet="Vault", ttl=0)
        if not vault_df.empty:
            vault_df.columns = [c.lower().strip() for c in vault_df.columns]
            bal_col = 'balance' if 'balance' in vault_df.columns else 'price_usd'
            vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
            
            # --- TIMEZONE SHIELD ---
            vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce').dt.tz_localize(None)
            vault_df = vault_df.dropna(subset=['timestamp', bal_col]).copy()

        for coin in ASSETS:
            with st.container():
                price = vance.scout_live_price(coin)
                if price:
                    st.divider()
                    st.header(f"🛰️ Sector: {coin}")
                    
                    asset_history = vault_df[vault_df['asset'].str.lower() == coin.lower()].copy()
                    cutoff = datetime.now().replace(tzinfo=None) - timedelta(hours=72)
                    asset_history = asset_history[asset_history['timestamp'] > cutoff]
                    
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(f"Live {coin}", f"${price:,.6f}")
                    
                    # 🏛️ KAEL: ANALYZE DATA
                    analysis = kael.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                    if analysis and analysis[0] is not None:
                        moving_avg, snap_pct, rsi_val, hook_found = analysis
                        c2.metric("Avg Window", f"${moving_avg:,.6f}")
                        st_color = "normal" if snap_pct > 0 else "inverse"
                        c3.metric("Snap %", f"{snap_pct:.3f}%", delta=f"{snap_pct:.3f}%", delta_color=st_color)
                        c4.metric("RSI (100)", f"{rsi_val:.1f}")
                        
                        # --- 📈 24H SECTOR VISUALIZATION ---
                        chart_cutoff = datetime.now().replace(tzinfo=None) - timedelta(hours=24)
                        chart_data = asset_history[asset_history['timestamp'] > chart_cutoff].copy()

                        if not chart_data.empty:
                            chart_df = chart_data[['timestamp', bal_col]].rename(columns={bal_col: 'Price'})
                            line_chart = alt.Chart(chart_df).mark_line(
                                color="#00ff00" if snap_pct > 0 else "#ff4b4b",
                                strokeWidth=2
                            ).encode(
                                x=alt.X('timestamp:T', title='Timeline (Last 24h)'),
                                y=alt.Y('Price:Q', title='Price ($)', scale=alt.Scale(zero=False)),
                                tooltip=['timestamp', alt.Tooltip('Price:Q', format=',.6f')]
                            ).properties(height=200, width="container").interactive()
                            
                            st.altair_chart(line_chart, use_container_width=True)
                        else:
                            st.caption("Insufficient 24h data for Sector Graph.")

                        st.divider()
                        st.subheader(f"Jace: {coin} Execution")
                        
                        # 🏛️ JACE: EXECUTE DECISION
                        outcome, action_data = jace.execute_trade(
                            coin, price, moving_avg, rsi_val, hook_found, live_ledger_df
                        )
                        
                        # --- 🏛️ PIPER: ACCOUNTING OFFICE SYNC ---
                        
                        # 1. NEW BUY LOGGING (Surgical Fix for Column Mismatch)
                        if outcome == "BUY" and action_data:
                            # 8-Column Institutional Map
                            cols = ['timestamp', 'asset', 'type', 'price', 'wager', 'result', 'profit_usd', 'result_clean']
                            
                            # Build the new row explicitly
                            new_row = pd.DataFrame([action_data], columns=cols)
                            
                            # Harmonize the existing ledger to match headers
                            if live_ledger_df.empty:
                                live_ledger_df = pd.DataFrame(columns=cols)
                            else:
                                live_ledger_df.columns = [c.lower().strip() for c in live_ledger_df.columns]

                            updated_df = pd.concat([live_ledger_df, new_row], ignore_index=True)
                            conn.update(worksheet="Ledger", data=updated_df)
                            st.success(f"🚀 NEW TRADE LOGGED: {coin} at ${price:.6f}")
                            st.rerun()

                        # 2. PEAK UPDATING
                        elif outcome == "PEAK_UPDATE" and action_data:
                            idx = action_data['index']
                            # Normalize column names before updating to avoid KeyErrors
                            live_ledger_df.columns = [c.lower().strip() for c in live_ledger_df.columns]
                            live_ledger_df.at[idx, 'result'] = action_data['new_peak']
                            conn.update(worksheet="Ledger", data=live_ledger_df)
                            st.toast(f"📈 {coin} Peak Updated: ${action_data['new_peak']:.6f}", icon="🚀")

                        # 3. TRADE CLOSING
                        elif outcome == "CLOSE" and action_data:
                            idx = action_data['index']
                            live_ledger_df.columns = [c.lower().strip() for c in live_ledger_df.columns]
                            live_ledger_df.at[idx, 'result_clean'] = "CLOSED"
                            live_ledger_df.at[idx, 'profit_usd'] = action_data['profit_usd']
                            live_ledger_df.at[idx, 'result'] = action_data.get('price', price)
                            conn.update(worksheet="Ledger", data=live_ledger_df)
                            st.warning(f"🎯 TRADE CLOSED: {coin} ({action_data['reason']})")
                            st.rerun()

                        # --- DISPLAY STATUS ---
                        if outcome == "HOLDING":
                            st.info(f"⏳ Jace is guarding the trend. Tracking Trailing Profit...")
                        elif outcome == "SCANNING":
                            st.write(f"⚖️ Jace is scanning {coin} sectors...")
                        else:
                            st.write(f"🛡️ Current Sector Status: {outcome}")

                    else:
                        c2.info(f"📡 {coin}: Scouting...")
    except Exception as e:
        st.error(f"Sentinel System Error: {e}")

# --- 🧾 TAB 2: THE ACCOUNTING OFFICE ---
with tab2:
    st.title("💼 Alt-Sentinel: Executive Summary")
    try:
        v_df = conn.read(worksheet="Vault", ttl=0)
        current_prices = {}
        ticker_map = {"XRP": "XRP", "STELLAR": "XLM", "XLM": "XLM", "HEDERA": "HBAR", "HBAR": "HBAR"}
        
        if not v_df.empty:
            v_df.columns = [str(c).strip().upper() for c in v_df.columns]
            for asset_name in ASSETS:
                name_upper = asset_name.upper()
                asset_rows = v_df[v_df['ASSET'].str.strip().str.upper() == name_upper]
                if not asset_rows.empty:
                    raw_price = asset_rows.iloc[-1]['BALANCE']
                    try:
                        price_val = float(str(raw_price).replace(',', '').replace('$', ''))
                        current_prices[name_upper] = price_val
                        ticker = ticker_map.get(name_upper)
                        if ticker: current_prices[ticker] = price_val
                    except: continue

        for asset_name in ASSETS:
            name_up = asset_name.upper()
            if name_up not in current_prices:
                p = vance.scout_live_price(asset_name)
                if p:
                    current_prices[name_up] = p
                    t = ticker_map.get(name_up)
                    if t: current_prices[t] = p
        
        ledger = piper.get_firm_ledger(conn, prices_dict=current_prices)
        
        if ledger and isinstance(ledger, dict):
            unrealized_pl, _ = piper.calculate_unrealized(ledger['trades_df'], current_prices)
            total_equity = ledger['vault_cash'] + unrealized_pl
            
            st.subheader("📊 Operational Health")
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vault Value", f"£{total_equity:,.2f}")
            m2.metric("Tradable", f"£{ledger['tradable_balance']:,.2f}")
            m3.metric("Tax Reserve", f"£{ledger['tax_pot']:,.2f}")
            m4.metric("Burn", f"£{ledger.get('burn', 0):,.2f}")

            st.divider()
            st.subheader("📜 Master Execution Ledger")
            desk_df = piper.format_institutional_ledger(ledger['trades_df'], current_prices)
            
            if not desk_df.empty:
                st.dataframe(
                    desk_df.sort_index(ascending=False).style.map(
                        lambda x: f'color: {"#00ff00" if x > 0 else "#ff4b4b" if x < 0 else "white"}', 
                        subset=['Return (%)', 'P/L ($)']
                    ).format({
                        'Entry Price': '${:,.6f}', 'MTM Price': '${:,.6f}',
                        'Return (%)': '{:,.2f}%', 'P/L ($)': '£{:,.2f}'
                    }),
                    width="stretch",
                    height=450
                )
            else:
                st.info("No trade data detected.")
                
    except Exception as e:
        st.error(f"Executive Office Error: {e}")
