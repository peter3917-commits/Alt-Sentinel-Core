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
        
    vault_sheet = client.open_by_key(sheet_id).worksheet("Vault")
    ledger_sheet = client.open_by_key(sheet_id).worksheet("Ledger")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

# --- A. VANCE: FETCH DATA & SYNC VAULT ---
raw_vault = vault_sheet.get_all_records()
df = pd.DataFrame(raw_vault)

if not df.empty:
    # Ensure capitalization matches logic
    df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    last_ts = datetime.utcnow() - timedelta(hours=50)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

now = datetime.utcnow()

# --- GAP HEALER (No changes to logic) ---
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
raw_ledger = ledger_sheet.get_all_records()
ledger_df = pd.DataFrame(raw_ledger)

# Clean ledger column names for Jace
if not ledger_df.empty:
    ledger_df.columns = [c.lower().strip() for c in ledger_df.columns]

for asset_name in ASSETS.keys():
    asset_df = df[df['Asset'] == asset_name].copy()
    if not asset_df.empty:
        # 🏛️ KAEL: ANALYZE DATA
        analysis = kael.check_for_snap(asset_name, float(asset_df['Balance'].iloc[-1]), asset_df.rename(columns={"Balance": "price_usd"}))
        
        if analysis and analysis[0] is not None:
            moving_avg, snap_pct, rsi_val, hook_found = analysis
            current_price = float(asset_df['Balance'].iloc[-1])
            
            # 🏛️ JACE: EXECUTE TRADE
            outcome, action_data = jace.execute_trade(
                asset_name, current_price, moving_avg, rsi_val, hook_found, ledger_df
            )
            
            # --- C. LEDGER UPDATER (Handling Jace's Returns) ---
            # Columns: 1:ts, 2:asset, 3:type, 4:price, 5:wager, 6:result(peak), 7:profit_usd, 8:result_clean
            if outcome == "BUY":
                # action_data is a list of 8 items. append_row handles this perfectly.
                ledger_sheet.append_row(action_data)
                print(f"🚀 {asset_name}: Position Opened at ${current_price:.6f}")
                
            elif outcome == "CLOSE":
                idx = action_data['index'] + 2 # Adjust for header row and 0-indexing
                # Update Result (Column 6), Profit (Column 7), and Status (Column 8)
                ledger_sheet.update_cell(idx, 6, action_data.get('price', current_price))
                ledger_sheet.update_cell(idx, 7, action_data['profit_usd'])
                ledger_sheet.update_cell(idx, 8, "CLOSED")
                print(f"💰 {asset_name}: Closed via {action_data['reason']}. PnL: {action_data['profit_usd']:.2f}%")

            elif outcome == "PEAK_UPDATE":
                idx = action_data['index'] + 2
                # Update the Peak Price in Column 6 (result)
                ledger_sheet.update_cell(idx, 6, action_data['new_peak'])
                print(f"📈 {asset_name}: New Peak Recorded: ${action_data['new_peak']:.6f}")

            print(f"Sect: {asset_name} | Price: ${current_price:.6f} | RSI: {rsi_val:.1f} | Jace: {outcome}")

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
