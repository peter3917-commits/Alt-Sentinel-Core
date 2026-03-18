import pandas as pd
from datetime import datetime, timedelta
import gspread
from google.oauth2.service_account import Credentials
import os, json, requests
import vance, kael, jace, piper, brian 

# 1. 🏛️ SETUP AUTH - ALT-SENTINEL CORE
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
        
    sheet = client.open_by_key(sheet_id).worksheet("Vault")
except Exception as e:
    print(f"❌ Auth Error: {e}")
    exit(1)

# --- 🛰️ THE MAIN ENGINE ---

# A. VANCE: FETCH & SYNC DATA
raw_data = sheet.get_all_records()
df = pd.DataFrame(raw_data)

# Standardize Columns for the Firm
if not df.empty:
    df.columns = [str(c).strip().title() for c in df.columns]
    df['Timestamp'] = pd.to_datetime(df['Timestamp'])
    last_ts = df['Timestamp'].max()
else:
    last_ts = datetime.utcnow() - timedelta(hours=50)
    df = pd.DataFrame(columns=["Staff", "Timestamp", "Asset", "Price_Usd"])

now = datetime.utcnow()
ASSETS = ["XRP", "XLM", "HBAR"]

print(f"🛰️ Vance: Commencing scout mission for {ASSETS}...")

# B. SPOT PRICE INJECTION
new_records = []
for coin in ASSETS:
    price = vance.scout_live_price(coin)
    if price:
        new_records.append({
            "Staff": "Vance (Background)", 
            "Timestamp": now, 
            "Asset": coin.upper(), 
            "Price_Usd": float(price)
        })
        print(f"✅ {coin} spotted at ${price:,.6f}")

if new_records:
    live_df = pd.DataFrame(new_records)
    df = pd.concat([df, live_df], ignore_index=True)

# C. KAEL & JACE: SECTOR ANALYSIS (PRE-COMPUTE)
# This ensures Jace is ready the moment you open the Streamlit App
for coin in ASSETS:
    asset_df = df[df['Asset'] == coin.upper()].copy()
    if len(asset_df) > 10:
        current_price = float(asset_df['Price_Usd'].iloc[-1])
        # Note: Kael/Jace logic can be triggered here if you want auto-execution 
        # but for now, we are just hardening the data Vault.
        print(f"📊 Sector {coin} Hardened. Depth: {len(asset_df)} points.")

# D. SHRED & SYNC (Keep last 72 hours only to prevent Sheet Bloat)
cutoff = datetime.utcnow() - timedelta(hours=72)
df = df[df['Timestamp'] > cutoff]

# Final Cleanup and Formatting
if not df.empty:
    df = df.drop_duplicates(subset=['Timestamp', 'Asset']).sort_values('Timestamp')
    df_sync = df[['Staff', 'Timestamp', 'Asset', 'Price_Usd']].copy()
    df_sync['Timestamp'] = df_sync['Timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
    
    # Prepare for GSheets Update
    data_to_save = [df_sync.columns.values.tolist()] + df_sync.values.tolist()
    try:
        sheet.clear()
        sheet.update(range_name='A1', values=data_to_save)
        print(f"✅ Vault synchronized. Current Depth: {len(df_sync)} rows.")
    except Exception as e:
        print(f"⚠️ Vault sync delay: {e}")
