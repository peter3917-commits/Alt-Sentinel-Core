import vance
import brian 
import claw  # <--- 🦅 ADDED CLAW
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
    last_ts_str = last_row[1]
    last_ts = pd.to_datetime(last_ts_str).replace(tzinfo=timezone.utc)
    
    time_diff = now_utc - last_ts
    
    if time_diff > timedelta(minutes=6):
        gap_minutes = int(time_diff.total_seconds() / 60)
        print(f"🕵️ Gap detected: {gap_minutes} minutes. Attempting backfill...")
        
        for i in range(5, gap_minutes, 5):
            target_time = last_ts + timedelta(minutes=i)
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
    print(f"⚠️ Heartbeat check skipped: {e}")

# --- 🚀 LIVE COLLECTION & AUTONOMOUS HARVEST ---
for coin in ASSETS:
    try:
        price = vance.scout_live_price(coin)
        if price:
            new_records.append({
                "staff": "Vance",
                "timestamp": now_utc.strftime('%Y-%m-%d %H:%M:%S'),
                "asset": coin.upper(),
                "price_usd": price
            })
            print(f"🛰️ Scouted {coin}: ${price}")

            try:
                # Brian targets the Harvester tab via full_spreadsheet
                brian.execute_autonomous_harvest(full_spreadsheet, coin.upper(), price)
            except Exception as b_err:
                print(f"⚠️ Brian skipped harvest: {b_err}")
        else:
            print(f"⚠️ Vance returned no price for {coin}")
    except Exception as e:
        print(f"❌ Failed to scout {coin}: {e}")

# --- 🛰️ THE PRECISION ENGINE (Vault Update) ---
if new_records:
    new_records.sort(key=lambda x: x['timestamp'])
    rows_to_append = [[r["staff"], r["timestamp"], r["asset"], r["price_usd"]] for r in new_records]
    try:
        vault_sheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        print(f"✅ Vault updated: +{len(rows_to_append)} records.")
        
        # 🧹 Tidy Up
        all_values = vault_sheet.get_all_values()
        if len(all_values) > 1: 
            headers = [h.lower().strip() for h in all_values[0]]
            ts_idx = headers.index("timestamp") if "timestamp" in headers else 1
            cutoff = datetime.now(timezone.utc) - timedelta(hours=48)
            
            rows_to_delete = 0
            for row in all_values[1:]:
                try:
                    row_ts = pd.to_datetime(row[ts_idx]).replace(tzinfo=timezone.utc)
                    if row_ts < cutoff: rows_to_delete += 1
                    else: break 
                except: break
            
            if rows_to_delete > 0:
                vault_sheet.delete_rows(2, rows_to_delete + 1)
                print(f"🧹 Removed {rows_to_delete} old records.")
    except Exception as e:
        print(f"⚠️ Vault update failed: {e}")

# --- 🦅 THE CLAW SENTIMENT SCAN (Log Update) ---
try:
    print("🦅 Claw is scanning sentiment for XRP...")
    scout = claw.Claw()
    risk_val, headline, source = scout.calculate_vibe("XRP")
    
    # FIX: Lock onto "Claw_Log" by name so it never writes to Harvester_Log
    try:
        claw_log_sheet = full_spreadsheet.worksheet("Claw_Log")
    except:
        # Fallback to the original GID index only if the name lookup fails
        claw_log_sheet = full_spreadsheet.get_worksheet(2) 

    # SAFETY CHECK: If the title contains 'harvest', abort the write to prevent mixed data
    if "harvest" in claw_log_sheet.title.lower():
        print(f"❌ ROUTING ERROR: Index 2 is currently '{claw_log_sheet.title}'. Aborting Claw write to prevent corruption.")
    else:
        new_claw_row = [
            now_utc.strftime('%Y-%m-%d %H:%M:%S'),
            f"{risk_val}%",
            "BEARISH" if risk_val > 60 else "BULLISH" if risk_val < 40 else "NEUTRAL",
            headline[:100],
            source
        ]
        claw_log_sheet.append_row(new_claw_row, value_input_option='USER_ENTERED')
        print(f"✅ Claw sentiment logged successfully to '{claw_log_sheet.title}': {risk_val}%")

except Exception as claw_err:
    print(f"⚠️ Claw skip (Non-critical): {claw_err}")
