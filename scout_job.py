import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os, json, requests
import vance, kael, jace  # AGENT IDENTITIES

# 1. SETUP AUTH
try:
    creds_dict = json.loads(os.environ['GSHEETS_SECRET'])
    creds = Credentials.from_service_account_info(creds_dict, scopes=[
        "https://www.googleapis.com/auth/spreadsheets", 
        "https://www.googleapis.com/auth/drive"
    ])
    client = gspread.authorize(creds)
    
    sheet_id = os.environ.get('GSHEET_ID')
    if not sheet_id:
        raise ValueError("GSHEET_ID environment variable is missing!")
        
    # Connect to the two critical sheets
    vault_sheet = client.open_by_key(sheet_id).worksheet("Vault")
    ledger_sheet = client.open_by_key(sheet_id).worksheet("Ledger")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

# --- A. VANCE: FETCH DATA & SYNC VAULT ---
raw_vault = vault_sheet.get_all_records()
df = pd.DataFrame(raw_vault)

if not df.empty:
    df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    last_ts = datetime.utcnow() - timedelta(hours=50)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

now = datetime.utcnow()

# --- GAP HEALER (No changes to your logic) ---
gap_seconds = (now - last_ts).total_seconds()
if gap_seconds > 420 and not df.empty:
    missing_slots = int(gap_seconds // 300)
    for i in range(1, missing_slots + 1):
        heal_ts = last_ts + timedelta(minutes=5 * i)
        for asset_name in ["XRP", "XLM", "HBAR"]:
            last_price = df[df['Asset'] == asset_name]['Balance'].iloc[-1] if not df[df['Asset'] == asset_name].empty else 0
            df = pd.concat([df, pd.DataFrame([{"Staff": "Vance (Heal)", "Timestamp": heal_ts, "Asset": asset_name, "Balance": float(last_price)}])], ignore_index=True)

# ADD CURRENT PRICES
ASSETS = {"XRP": "ripple", "XLM": "stellar", "HBAR": "hedera-hashgraph"}
for asset_name in ASSETS.keys():
    try:
        price = vance.scout_live_price(asset_name)
        if price:
            df = pd.concat([df, pd.DataFrame([{"Staff": "Vance (Background)", "Timestamp": now, "Asset": asset_name, "Balance": float(price)}])], ignore_index=True)
    except Exception as e:
        print(f"⚠️ Vance failed {asset_name}: {e}")

df = df.drop_duplicates(subset=['Timestamp', 'Asset']).sort_values('Timestamp')

# --- B. KAEL & JACE: SECTOR ANALYSIS & LEDGER MANAGEMENT ---
# Fetch Ledger data once to pass to Jace
raw_ledger = ledger_sheet.get_all_records()
ledger_df = pd.DataFrame(raw_ledger)

for asset_name in ASSETS.keys():
    asset_df = df[df['Asset'] == asset_name].copy()
    if not asset_df.empty:
        asset_df['Balance'] = pd.to_numeric(asset_df['Balance'])
        magnet = asset_df['Balance'].tail(288).mean() # 24hr Magnet
        current_price = float(asset_df['Balance'].iloc[-1])
        
        # JACE EXECUTION
        pnl, live_pnl, outcome, action_data = jace.execute_trade(
            asset_name, current_price, magnet, history_df=asset_df, ledger_df=ledger_df
        )
        
        # --- C. LEDGER UPDATER (Handling Jace's Returns) ---
        if outcome == "BUY":
            ledger_sheet.append_row(action_data)
            print(f"🚀 {asset_name}: Position Opened at ${current_price}")
            
        elif outcome in ["LOSS", "WIN_TRAIL", "WIN_RSI"]:
            idx = action_data['index'] + 2 # Adjust for header/1-base
            ledger_sheet.update_cell(idx, 6, action_data['price'])        # Final Price
            ledger_sheet.update_cell(idx, 7, action_data['profit_usd'])  # Final PnL
            ledger_sheet.update_cell(idx, 8, "CLOSED")                  # Close Status
            print(f"💰 {asset_name}: Position {outcome} Closed. PnL: £{action_data['profit_usd']:.2f}")

        elif outcome == "PEAK_UPDATE":
            idx = action_data['index'] + 2
            ledger_sheet.update_cell(idx, 6, action_data['new_peak']) # Update Peak in 'result' col
            print(f"📈 {asset_name}: New Peak Recorded: ${action_data['new_peak']:.4f}")

        print(f"Sect: {asset_name} | Price: ${current_price:.6f} | Magnet: ${magnet:.6f} | Jace: {outcome}")

# --- D. THE JANITOR & VAULT SYNC ---
cutoff = datetime.utcnow() - timedelta(hours=50)
df = df[df['Timestamp'] > cutoff].sort_values(by=['Timestamp', 'Asset'])

if not df.empty:
    df_sync = df[['Staff', 'Timestamp', 'Asset', 'Balance']].copy()
    df_sync['Timestamp'] = df_sync['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    try:
        vault_sheet.clear()
        vault_sheet.update(range_name='A1', values=[df_sync.columns.values.tolist()] + df_sync.values.tolist())
        print(f"✅ Vault synced. Rows: {len(df_sync)}")
    except Exception as e:
        print(f"⚠️ Sync delay: {e}")
