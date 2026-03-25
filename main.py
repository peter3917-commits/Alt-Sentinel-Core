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
    
    # Global Heartbeat (Refreshes UI to see GitHub Action updates)
    st_autorefresh(interval=300000, key="global_heartbeat")
    
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
        except:
            st.sidebar.warning("Claw: Data Syncing...")

    if not vault_df.empty:
        for coin in ASSETS:
            # OBSERVER MODE: Pull the latest price from your internal vault_df
            coin_history = vault_df[vault_df['asset'] == coin.upper()].copy()
            
            if not coin_history.empty:
                latest_entry = coin_history.iloc[-1]
                price = latest_entry[bal_col]
                
                st.divider()
                st.header(f"🛰️ Sector: {coin}")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Last Scouted", f"${price:,.6f}")
                
                # Analysis via Kael
                analysis = kael.check_for_snap(coin, price, coin_history.rename(columns={bal_col: "price_usd"}))
                if analysis and analysis[0] is not None:
                    ma, snap, rsi, hook = analysis
                    c2.metric("Moving Avg", f"${ma:,.6f}")
                    c3.metric("Snap %", f"{snap:.3f}%")
                    c4.metric("RSI", f"{rsi:.1f}")
                    
                    # Trend Chart
                    chart_data = coin_history.tail(100).rename(columns={bal_col: 'Price'})
                    line = alt.Chart(chart_data).mark_line(color="#00d4ff", strokeWidth=3).encode(
                        x='timestamp:T', y=alt.Y('Price:Q', scale=alt.Scale(zero=False))
                    ).properties(height=300)
                    st.altair_chart(line, width="stretch")

# --- 🧾 TAB 2: ACCOUNTING OFFICE ---
with tab2:
    st.header("🧾 Firm Ledger & Accounting")
    try:
        piper.show_performance_metrics(ledger_data)
    except Exception as e:
        st.error(f"Piper Error: {e}")

# --- 🚜 TAB 3: HARVESTER ---
with tab3:
    st.header("🚜 Autonomous Harvester: HBAR Grid Monitor")
    
    if not vault_df.empty:
        hbar_all = vault_df[vault_df['asset'] == 'HBAR'].copy()
        if not hbar_all.empty:
            hbar_all = hbar_all.rename(columns={bal_col: 'Price'})
            
            # 24h Filter with Fallback
            hbar_history = hbar_all[hbar_all['timestamp'] >= (datetime.now() - timedelta(hours=24))].copy()
            if hbar_history.empty: hbar_history = hbar_all.tail(100)

            # Price Line (Cyan)
            price_line = alt.Chart(hbar_history).mark_line(
                color='#00d4ff', strokeWidth=3, point=alt.OverlayMarkDef(size=30)
            ).encode(
                x=alt.X('timestamp:T', title="Timeline"),
                y=alt.Y('Price:Q', title="Price ($)", scale=alt.Scale(zero=False))
            )

            # Brian's Grid
            if not raw_harvester_log.empty:
                brian_hbar = raw_harvester_log[raw_harvester_log['sector'] == 'HBAR'].copy()
                grid_rules = alt.Chart(brian_hbar).mark_rule(strokeDash=[6, 4], size=2).encode(
                    y='price:Q',
                    color=alt.condition(alt.datum.type == 'SELL', alt.value('#ff4b4b'), alt.value('#00ff00'))
                )

                grid_labels = alt.Chart(brian_hbar).mark_text(align='left', dx=10, fontSize=12, fontWeight='bold').encode(
                    y='price:Q', x=alt.value(750), text=alt.Text('price:Q', format='.5f'),
                    color=alt.condition(alt.datum.type == 'SELL', alt.value('#ff4b4b'), alt.value('#00ff00'))
                )

                st.altair_chart((price_line + grid_rules + grid_labels).properties(height=500).interactive(), width="stretch")
            else:
                st.altair_chart(price_line.properties(height=500).interactive(), width="stretch")

    st.divider()
    st.subheader("📜 Brian's Live Level Status")
    st.dataframe(raw_harvester_log, width="stretch")
