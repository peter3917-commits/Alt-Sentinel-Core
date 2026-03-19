import vance
import brian 
from datetime import datetime, timedelta, timezone
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
import json
import time

# --- 🔑 AUTHENTICATION & SHEET DEFINITION ---
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if os.path.exists("creds.json"):
    creds = Credentials.from_service_account_file("creds.json", scopes=scope)
else:
    google_creds = os.getenv("GSHEETS_SECRET")
    if google_creds:
        try:
            creds_dict = json.loads(google_creds)
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        except json.JSONDecodeError:
            raise Exception("❌ CRITICAL: GSHEETS_SECRET found but it is not valid JSON.")
    else:
        raise Exception("❌ CRITICAL: No Google Credentials found.")

client = gspread.authorize(creds)
SHEET_ID = os.getenv("GSHEET_ID", "15pD60KIjHB7GNEwlbsYg-STclQ0wKYOA7zkD5oYcaJQ")
full_spreadsheet = client.open_by_key(SHEET_ID)
vault_sheet = full_spreadsheet.get_worksheet(0) # GID 0 (Vault)

# --- 🛰️ INITIALIZATION ---
new_records = []  
ASSETS = ["XRP", "XLM", "HBAR"]
now_utc = datetime.now(timezone.utc)

# --- 💓 HEARTBEAT GAP-FILL LOGIC ---
try:
    print("💓 Checking Vault Heartbeat...")
    last_row = vault_sheet.get_all_values()[-1]
    # Assuming Timestamp is in column 2 (index 1)
    last_ts_str = last_row[1]
    last_ts = pd.to_datetime(last_ts_str).replace(tzinfo=timezone.utc)
    
    time_diff = now_utc - last_ts
    
    # If the gap is 6+ minutes, we missed a 5-minute ping.
    if time_diff > timedelta(minutes=6):
        gap_minutes = int(time_diff.total_seconds() / 60)
        print(f"🕵️ Gap detected: {gap_minutes} minutes. Attempting backfill...")
        
        # We loop through every 5-minute block we missed
        for i in range(5, gap_minutes, 5):
            target_time = last_ts + timedelta(minutes=i)
            # Binance needs timestamp in Unix Milliseconds
            ts_ms = int(target_time.timestamp() * 1000)
            
            for coin in ASSETS:
                h_price = vance.scout_historic_price(coin, ts_ms)
                if h_price:
                    new_records.append({
                        "staff": "Vance_Backfill",
                        "timestamp": target_time.strftime('%Y-%m-%d %H:%M:%S'),
                        "asset": coin.upper(),
                        "price_usd": h_price
                    })
        print(f"📦 Backfill prepared: {len(new_records)} missing records found.")
except Exception as e:
    print(f"⚠️ Heartbeat check skipped (First run or Error): {e}")

# --- 🚀 LIVE COLLECTION & AUTONOMOUS HARVEST ---
for coin in ASSETS:
    try:
        price = vance.scout_live_price(coin)
        if price:
            # 1. LOG FOR THE VAULT
            new_records.append({
                "staff": "Vance",
                "timestamp": now_utc.strftime('%Y-%m-%d %H:%M:%S'),
                "asset": coin.upper(),
                "price_usd": price
            })
            print(f"🛰️ Scouted {coin}: ${price}")

            # 2. 🚜 BRIAN'S NIGHT SHIFT
            try:
                brian.execute_autonomous_harvest(full_spreadsheet, coin.upper(), price)
            except Exception as b_err:
                print(f"⚠️ Brian skipped harvest check for {coin}: {b_err}")
        else:
            print(f"⚠️ Vance returned no price for {coin}")
    except Exception as e:
        print(f"❌ Failed to scout {coin}: {e}")

# --- 🛰️ THE PRECISION ENGINE (Vault Update) ---
if new_records:
    # Sort records by timestamp to keep the Google Sheet orderly
    new_records.sort(key=lambda x: x['timestamp'])
    
    rows_to_append = [[r["staff"], r["timestamp"], r["asset"], r["price_usd"]] for r in new_records]
    try:
        vault_sheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        print(f"✅ Vault updated: +{len(rows_to_append)} records (Live + Gaps).")
        
        # --- 🧹 TIDY UP LOGIC (Keeping 48 hours) ---
        all_values = vault_sheet.get_all_values()
        if len(all_values) > 1: 
            headers = [h.lower().strip() for h in all_values[0]]
            rows = all_values[1:]
            ts_idx = headers.index("timestamp") if "timestamp" in headers else 1
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            
            rows_to_delete = 0
            for row in rows:
                try:
                    row_ts = pd.to_datetime(row[ts_idx]).replace(tzinfo=timezone.utc)
                    if row_ts < cutoff: rows_to_delete += 1
                    else: break 
                except:
                    if len(row) > ts_idx and not row[ts_idx]: rows_to_delete += 1
                    else: break
            
            if rows_to_delete > 0:
                vault_sheet.delete_rows(2, rows_to_delete + 1)
                print(f"🧹 Removed {rows_to_delete} old records.")
    except Exception as e:
        print(f"⚠️ Vault update failed: {e}")
