import os
import json
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import vance  # Vance still does the scouting!

# --- 🛰️ SCOUT CONFIGURATION ---
ASSETS = ["XRP", "XLM", "HBAR"]

def run_silent_scout():
    print("🛰️ Vance: Commencing background scout mission...")
    
    # 1. 🔑 AUTHENTICATION (The Silent Way)
    # We pull the secret from the GitHub environment
    try:
        creds_json = json.loads(os.environ["GSHEETS_SECRET"])
        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(creds_json, scopes=scopes)
        client = gspread.authorize(creds)
        
        # 2. 📖 OPEN THE VAULT
        sheet_id = os.environ["GSHEET_ID"]
        spreadsheet = client.open_by_key(sheet_id)
        vault_sheet = spreadsheet.worksheet("Vault")
        
        # 3. 🎯 THE SCOUTING LOOP
        for coin in ASSETS:
            price = vance.scout_live_price(coin)
            if price:
                print(f"✅ {coin} spotted at ${price:,.6f}")
                
                # Create the row for Google Sheets
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_row = [timestamp, coin.upper(), float(price)]
                
                # Vance writes directly to the Sheet
                vault_sheet.append_row(new_row)
                print(f"⚓ {coin} anchored to Vault.")
            else:
                print(f"⚠️ {coin} scout failed.")

    except Exception as e:
        print(f"❌ Scout Mission Aborted: {e}")

if __name__ == "__main__":
    run_silent_scout()
