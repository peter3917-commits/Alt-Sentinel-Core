import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os, json, requests
import vance, kael, jace  # NEW AGENT IDENTITIES

# 1. SETUP AUTH - SECURED FOR ALT-SENTINEL
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
        
    # Connect to the Vault sheet
    sheet = client.open_by_key(sheet_id).worksheet("Vault")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

# --- THE ALT-SENTINEL ENGINE ---

# A. VANCE: FETCH DATA & SYNC VAULT
raw_data = sheet.get_all_records()
df = pd.DataFrame(raw_data)

if not df.empty:
    # 🛡️ NORMALIZATION SHIELD (Ensures 'Asset' column is capitalized correctly)
    df.columns = [c.capitalize() if c.lower() == 'asset' else c for c in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    last_ts = datetime.utcnow() - timedelta(hours=50)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Balance"])

now = datetime.utcnow()

# --- ALT-SENTINEL SECTOR CONFIGURATION ---
ASSETS = {
    "XRP": "ripple",
    "XLM": "stellar",
    "HBAR": "hedera-hashgraph"
}

# Add current spot prices for all assets using Vance's logic
for asset_name, market_id in ASSETS.items():
    try:
        price = vance.scout_live_price(asset_name)
        if price:
            live_row = pd.DataFrame([{
                "Staff": "Vance (Background)", 
                "Timestamp": now, 
                "Asset": asset_name, 
                "Balance": float(price)
            }])
            df = pd.concat([df, live_row], ignore_index=True)
    except Exception as e:
        print(f"⚠️ Vance failed sector {asset_name}: {e}")

# Ensure we keep multi-asset records and remove exact duplicates
df = df.drop_duplicates(subset=['Timestamp', 'Asset']).sort_values('Timestamp')

# B. KAEL & JACE: SECTOR ANALYSIS & EXECUTION
for asset_name in ASSETS.keys():
    asset_df = df[df['Asset'] == asset_name].copy()
    if not asset_df.empty:
        asset_df['Balance'] = pd.to_numeric(asset_df['Balance'])
        
        # Kael calculates the "Magnet" using the last 576 points (exactly 48 hours)
        # Note: 48 hours * 12 pings/hr = 576 data points
        magnet = asset_df['Balance'].tail(576).mean()
        current_price = float(asset_df['Balance'].iloc[-1])
        
        # C. JACE: EXECUTE
        # Note: Background scout passes None for RSI/Ledger to trigger standard safety checks
        _, _, outcome, _ = jace.execute_trade(asset_name, current_price, magnet, history_df=asset_df)
        
        # High-precision console reporting
        print(f"Sect: {asset_name} | Price: ${current_price:.6f} | Magnet: ${magnet:.6f} | Jace: {outcome}")

# D. SHRED & HIGH-SPEED SYNC
# Keep 50 hours of data to ensure Kael's 48-hour magnet is always full
cutoff = datetime.utcnow() - timedelta(hours=50)
df = df[df['Timestamp'] > cutoff]

if not df.empty:
    df_sync = df[['Staff', 'Timestamp', 'Asset', 'Balance']].copy()
    df_sync['Timestamp'] = df_sync['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    data_to_save = [df_sync.columns.values.tolist()] + df_sync.values.tolist()
    try:
        sheet.clear()
        sheet.update(range_name='A1', values=data_to_save)
        print(f"✅ Alt-Sentinel Vault synced. Depth: {len(df_sync)} rows across 3 assets.")
    except Exception as e:
        print(f"⚠️ Vault sync delay: {e}")
