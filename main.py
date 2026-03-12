import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import vance, kael, jace, piper  # UPDATED: New Agent Identities
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
                    # PRECISION OVERHAUL: Changed to 6 decimal places for low-price assets
                    c1.metric(f"Live {coin}", f"${price:,.6f}")
                    
                    analysis = kael.check_for_snap(coin, price, asset_history.rename(columns={bal_col: "price_usd"}))
                    if analysis and analysis[0] is not None:
                        moving_avg, snap_pct, rsi_val, hook_found = analysis
                        c2.metric("Avg Window", f"${moving_avg:,.6f}") # Precision 6dp
                        st_color = "normal" if snap_pct > 0 else "inverse"
                        c3.metric("Snap %", f"{snap_pct:.3f}%", delta=f"{snap_pct:.3f}%", delta_color=st_color)
                        c4.metric("RSI (14)", f"{rsi_val:.1f}")
                        
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
                                tooltip=['timestamp', alt.Tooltip('Price:Q', format=',.6f')] # Precision Tooltip
                            ).properties(height=200, width="container").interactive()
                            
                            st.altair_chart(line_chart, use_container_width=True)
                        else:
                            st.caption("Insufficient 24h data for Sector Graph.")

                        st.divider()
                        st.subheader(f"Jace: {coin} Execution")
                        
                        gross, net, outcome, trade_data = jace.execute_trade(
                            coin, price, moving_avg, rsi=rsi_val, 
                            history_df=asset_history, ledger_df=live_ledger_df
                        )
                        
                        # --- GOOGLE SHEETS SYNC LOGIC ---
                        if outcome == "BUY" and trade_data:
                            new_row = pd.DataFrame([trade_data], columns=['timestamp','asset','type','price','wager','result','profit_usd'])
                            updated_df = pd.concat([live_ledger_df, new_row], ignore_index=True)
                            conn.update(worksheet="Ledger", data=updated_df)
                            st.success(f"🚀 NEW TRADE LOGGED: {coin}")
                            st.rerun()

                        elif outcome in ["WIN_MOONSHOT", "WIN_TRAILING", "LOSS"] and trade_data:
                            idx_to_update = trade_data['index']
                            live_ledger_df.at[idx_to_update, 'result'] = trade_data['result']
                            live_ledger_df.at[idx_to_update, 'profit_usd'] = trade_data['profit_usd']
                            conn.update(worksheet="Ledger", data=live_ledger_df)
                            st.warning(f"🎯 TRADE CLOSED: {coin} ({outcome})")
                            st.rerun()

                        # --- DISPLAY STATUS ---
                        if outcome == "OPEN":
                            st.info(f"⏳ Trade is OPEN. Floating P/L: £{net:.2f}")
                        elif "WIN" in outcome:
                            st.success(f"🎯 Outcome: {outcome} (£{net:.2f})")
                        elif outcome == "LOSS":
                            st.error(f"⚠️ Outcome: {outcome} (£{net:.2f})")
                        else:
                            st.write(f"⚖️ Jace is holding {coin}.")
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
        # UPDATED: Mapping for Alt-Sentinel Sector
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
                        # PRECISION OVERHAUL: Set to 6dp for the ledger view
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
