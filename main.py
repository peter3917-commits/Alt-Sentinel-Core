import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_autorefresh import st_autorefresh
import vance, kael, jace, piper, brian, claw  
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
    # Verified GIDs from conversation
    URL_VAULT = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
    URL_HARVESTER = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=2062418608"
    URL_CLAW = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=205181431" 
    
    try:
        df_vault = pd.read_csv(URL_VAULT)
        try:
            df_harvest = pd.read_csv(URL_HARVESTER)
        except:
            df_harvest = pd.DataFrame()
        try:
            df_claw = pd.read_csv(URL_CLAW)
        except:
            df_claw = pd.DataFrame()
        return df_vault, df_harvest, df_claw
    except Exception as e:
        st.error(f"Vault Sync Error: {e}")
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

@st.cache_data(ttl=60)
def fetch_ledger_data(_conn):
    return piper.get_firm_ledger(_conn)

# --- 🏛️ GLOBAL DATA INITIALIZATION ---
conn = st.connection("gsheets", type=GSheetsConnection)
raw_vault, raw_harvester_log, raw_claw_log = fetch_vault_data_direct()
ledger_data = fetch_ledger_data(conn)

# --- 🛡️ DATA HARDENING (VAULT) ---
vault_df = pd.DataFrame()
bal_col = 'price_usd'

if not raw_vault.empty:
    vault_df = raw_vault.copy()
    vault_df.columns = [str(c).lower().strip() for c in vault_df.columns]
    
    if 'asset' not in vault_df.columns:
        pot = [c for c in vault_df.columns if 'asset' in c or 'coin' in c]
        if pot: vault_df = vault_df.rename(columns={pot[0]: 'asset'})

    for c in ['price_usd', 'balance', 'price', 'balance2']:
        if c in vault_df.columns:
            bal_col = c
            break

    vault_df['timestamp'] = pd.to_datetime(vault_df['timestamp'], errors='coerce')
    vault_df[bal_col] = pd.to_numeric(vault_df[bal_col], errors='coerce')
    if 'asset' in vault_df.columns:
        vault_df['asset'] = vault_df['asset'].astype(str).str.upper().str.strip()
    vault_df = vault_df.dropna(subset=['timestamp', bal_col]).sort_values('timestamp')

# --- 📱 UI LAYOUT ---
tab1, tab2, tab3 = st.tabs(["🛰️ Sentinel Engine", "🧾 Accounting Office", "🚜 The Harvester"])

# --- 🛰️ TAB 1: SENTINEL ENGINE ---
with tab1:
    st.title("🏛️ Alt-Sentinel: High-Precision Desk")
    
    # --- 🦅 CLAW'S SIDEBAR ---
    st.sidebar.divider()
    st.sidebar.subheader("🦅 Claw's Lookout")
    risk_val = 50.0 
    
    if not raw_claw_log.empty:
        try:
            raw_claw_log.columns = [str(c).lower().strip() for c in raw_claw_log.columns]
            risk_col = 'assetrisk_score' if 'assetrisk_score' in raw_claw_log.columns else 'risk_score'
            risk_raw = str(raw_claw_log.tail(1)[risk_col].values[0])
            
            clean_risk = "".join(filter(lambda x: x.isdigit() or x == '.', risk_raw))
            if clean_risk:
                risk_val = float(clean_risk)
                st.sidebar.metric("Market Risk Score", f"{risk_val}%")
            else:
                st.sidebar.warning("Claw: Data Pending...")
        except:
            st.sidebar.warning("Claw: Data Formatting Issue")
    
    auto_trade = st.sidebar.toggle("Activate Vance Auto-Scout", value=False)
    if auto_trade:
        try:
            claw.update_claw_log(conn, ticker="XRP") 
        except Exception as e:
            st.sidebar.error(f"Claw Log Update Failed: {e}")
        st_autorefresh(interval=300000, key="vance_heartbeat")

    if not vault_df.empty and 'asset' in vault_df.columns:
        for coin in ASSETS:
            price = vance.scout_live_price(coin)
            if price:
                coin_history = vault_df[vault_df['asset'] == coin.upper()].copy()
                st.divider()
                st.header(f"🛰️ Sector: {coin}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Live Price", f"${price:,.6f}")
                
                analysis = kael.check_for_snap(coin, price, coin_history.rename(columns={bal_col: "price_usd"}))
                if analysis and analysis[0] is not None:
                    ma, snap, rsi, hook = analysis
                    c2.metric("Moving Avg", f"${ma:,.6f}")
                    c3.metric("Snap %", f"{snap:.3f}%")
                    c4.metric("RSI", f"{rsi:.1f}")
                    
                    chart_data = coin_history.tail(300).rename(columns={bal_col: 'Price'})
                    if not chart_data.empty:
                        line = alt.Chart(chart_data).mark_line(color="#00ff00" if snap > 0 else "#ff4b4b").encode(
                            x='timestamp:T', y=alt.Y('Price:Q', scale=alt.Scale(zero=False))
                        ).properties(height=300)
                        st.altair_chart(line, width='stretch')
                    
                    try:
                        jace.execute_trade(
                            asset=coin, current_price=price, average=ma, 
                            rsi=rsi, hook=hook, ledger_df=ledger_data['trades_df'], 
                            risk_multiplier=risk_val
                        )
                    except: pass

# --- 🧾 TAB 2: ACCOUNTING OFFICE ---
with tab2:
    st.header("🧾 Firm Ledger & Accounting")
    # FIX: Piper handles the table. Removing the second st.dataframe prevents the double call.
    try:
        piper.show_performance_metrics(ledger_data)
    except Exception as e:
        st.error(f"Piper Performance Metric Error: {e}")

# --- 🚜 TAB 3: HARVESTER ---
with tab3:
    st.header("🚜 Autonomous Harvester: Institutional HBAR Scan")
    
    # 1. 🛰️ DATA PREP: JOINING VAULT & LOG
    # We pull the 24-hour price history from the Vault
    if not vault_df.empty:
        hbar_history = vault_df[vault_df['asset'] == 'HBAR'].tail(500).copy()
        
        if not hbar_history.empty:
            # Create the Background Price Line (The "Movement")
            price_line = alt.Chart(hbar_history).mark_line(color='#ffaa00', opacity=0.4).encode(
                x=alt.X('timestamp:T', title="24-Hour Scan"),
                y=alt.Y(f'{bal_col}:Q', title="HBAR Price ($)", scale=alt.Scale(zero=False))
            )

            # 2. 🦅 ADDING BRIAN'S FEATURES (From the Harvester Log CSV)
            if not raw_harvester_log.empty:
                brian_data = raw_harvester_log[raw_harvester_log['sector'] == 'HBAR'].copy()
                brian_data['timestamp'] = pd.to_datetime(brian_data['timestamp'])
                
                # Plot Brian's calculated BUY/SELL levels as dots on the line
                features = alt.Chart(brian_data).mark_circle(size=80).encode(
                    x='timestamp:T',
                    y='price:Q',  # This is the target price from Brian's table
                    color=alt.condition(
                        alt.datum.type == 'BUY', 
                        alt.value('#00ff00'), # Green for Brian's Buy levels
                        alt.value('#ff4b4b')  # Red for Brian's Sell levels
                    ),
                    tooltip=['timestamp', 'level', 'type', 'price', 'status']
                )

                # Layer them together
                st.altair_chart((price_line + features).interactive(), use_container_width=True)
            else:
                st.altair_chart(price_line.interactive(), use_container_width=True)
                st.info("HBAR Price Line active. Waiting for Brian's harvest levels...")

    # 3. 📜 BRIAN'S RAW ACTIVITY LOG
    st.divider()
    st.subheader("📜 Brian's Harvest Levels (Last Scan)")
    if not raw_harvester_log.empty:
        st.dataframe(raw_harvester_log, width='stretch')
    else:
        st.info("No activity found in the Harvester Log.")
