import vance
from datetime import datetime, timedelta, UTC
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json

# --- 🔑 AUTHENTICATION & SHEET DEFINITION ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Logic to handle both local 'creds.json' and GitHub Secrets
if os.path.exists("creds.json"):
    creds = Credentials.from_service_account_file("creds.json", scopes=scope)
else:
    # 🎯 TARGET FIXED: Now looking for your specific GitHub Secret name
    google_creds = os.getenv("GSHEETS_JSON")
    if google_creds:
        creds_dict = json.loads(google_creds)
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    else:
        raise Exception("❌ CRITICAL: No Google Credentials found (creds.json or GSHEETS_JSON Secret).")

client = gspread.authorize(creds)
SHEET_ID = "15pD60KIjHB7GNEwlbsYg-STclQ0wKYOA7zkD5oYcaJQ"
sheet = client.open_by_key(SHEET_ID).sheet1 

# --- 🛰️ INITIALIZATION ---
new_records = []  
ASSETS = ["XRP", "XLM", "HBAR"]

# 🚀 THE COLLECTION
for coin in ASSETS:
    try:
        price = vance.scout_live_price(coin)
        if price:
            new_records.append({
                "staff": "Vance",
                "timestamp": datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S'),
                "asset": coin.upper(),
                "price_usd": price
            })
            print(f"🛰️ Scouted {coin}: ${price}")
        else:
            print(f"⚠️ Vance returned no price for {coin} (Possible API Rate Limit)")
    except Exception as e:
        print(f"❌ Failed to scout {coin}: {e}")

# --- 🛰️ THE PRECISION ENGINE ---
if new_records:
    rows_to_append = [
        [r["staff"], r["timestamp"], r["asset"], r["price_usd"]]
        for r in new_records
    ]
    
    try:
        sheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        print(f"✅ Vault updated: +{len(rows_to_append)} records.")
        
        # --- 🛡️ SAFETY BRAKE TIDY ---
        all_values = sheet.get_all_values()
        if len(all_values) > 1: # Basic check to ensure we have headers
            headers = [h.lower().strip() for h in all_values[0]]
            rows = all_values[1:]
            
            ts_idx = headers.index("timestamp") if "timestamp" in headers else 1
            cutoff = datetime.now(UTC) - timedelta(hours=48)
            
            rows_to_delete = 0
            for row in rows:
                try:
                    row_ts = pd.to_datetime(row[ts_idx]).replace(tzinfo=UTC)
                    if row_ts < cutoff:
                        rows_to_delete += 1
                    else:
                        break 
                except:
                    if len(row) > ts_idx and not row[ts_idx]: rows_to_delete += 1
                    else: break
            
            if rows_to_delete > 0:
                sheet.delete_rows(2, rows_to_delete + 1)
                print(f"🧹 Removed {rows_to_delete} old records.")
    except Exception as e:
        print(f"⚠️ Vault update failed: {e}")
else:
    print("🛑 API FETCH FAILED: Skipping Tidy-up to protect existing Vault data.")
