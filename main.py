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
                        st.altair_chart(line, use_container_width=True)

# --- 🧾 TAB 2: ACCOUNTING OFFICE ---
with tab2:
    st.header("🧾 Firm Ledger & Accounting")
    try:
        piper.show_performance_metrics(ledger_data)
    except Exception as e:
        st.error(f"Piper Performance Metric Error: {e}")

# --- 🚜 TAB 3: HARVESTER (FIXED PRICE LINE) ---
with tab3:
    st.header("🚜 Autonomous Harvester: HBAR Grid Monitor")
    
    if not vault_df.empty:
        # 1. 🕒 ROBUST TIME FILTERING
        # We ensure everything is in UTC or localized to match
        now = datetime.now()
        last_24h = now - timedelta(hours=24)
        
        # Filter for HBAR
        hbar_all = vault_df[vault_df['asset'] == 'HBAR'].copy()
        # Filter for last 24h
        hbar_history = hbar_all[hbar_all['timestamp'] >= last_24h].copy()

        # --- 🛠️ DEBUG ASSISTANT (Only shows if there's an issue) ---
        if hbar_history.empty:
            st.warning(f"⚠️ Price line missing: Found {len(hbar_all)} HBAR records, but 0 in the last 24 hours.")
            if not hbar_all.empty:
                st.info(f"Latest HBAR data point in Vault: {hbar_all['timestamp'].max()}")
                # Fallback: Show last 500 points regardless of time if 24h is empty
                hbar_history = hbar_all.tail(500)
        
        if not hbar_history.empty:
            # 2. Background Price Line (Vance)
            price_line = alt.Chart(hbar_history).mark_line(
                color='#ffffff', 
                strokeWidth=2,
                opacity=0.8
            ).encode(
                x=alt.X('timestamp:T', title="Timeline"),
                y=alt.Y(f'{bal_col}:Q', title="Price ($)", scale=alt.Scale(zero=False)),
                tooltip=['timestamp', f'{bal_col}']
            )

            # 3. Brian's Horizontal Grid Lines
            if not raw_harvester_log.empty:
                # Filter Brian's log for HBAR
                brian_hbar = raw_harvester_log[raw_harvester_log['sector'] == 'HBAR'].copy()
                
                grid_lines = alt.Chart(brian_hbar).mark_rule(strokeDash=[4, 4]).encode(
                    y='price:Q',
                    color=alt.condition(
                        alt.datum.type == 'SELL', 
                        alt.value('#ff4b4b'), # Red
                        alt.value('#00ff00')  # Green
                    ),
                    size=alt.value(1.5),
                    tooltip=['level', 'type', 'price', 'status']
                )

                # 4. Right-side Price Labels
                grid_labels = alt.Chart(brian_hbar).mark_text(
                    align='left', dx=10, fontSize=12, fontWeight='bold'
                ).encode(
                    y='price:Q',
                    x=alt.value(800), # Push to right edge
                    text=alt.Text('price:Q', format='.5f'),
                    color=alt.condition(alt.datum.type == 'SELL', alt.value('#ff4b4b'), alt.value('#00ff00'))
                )

                # Layer and render
                st.altair_chart((price_line + grid_lines + grid_labels).properties(height=500), use_container_width=True)
            else:
                st.altair_chart(price_line.properties(height=500), use_container_width=True)
    else:
        st.error("Vault Data is empty. Vance hasn't reported any prices yet.")

    st.divider()
    st.subheader("📜 Brian's Live Level Status")
    st.dataframe(raw_harvester_log, use_container_width=True)
