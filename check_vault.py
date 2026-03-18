import vance
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

# 1. TEST VANCE
print("Step 1: Testing Vance's Scouting...")
price = vance.scout_live_price("XRP")
if price:
    print(f"✅ Vance found XRP at ${price}")
else:
    print("❌ Vance failed to find a price. Check internet or API limits.")

# 2. TEST AUTHENTICATION
print("\nStep 2: Testing Vault Authentication...")
try:
    # Use the same credentials your scout_job.py uses
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scope)
    client = gspread.authorize(creds)
    print("✅ Credentials accepted by Google.")
except Exception as e:
    print(f"❌ Authentication Failed: {e}")

# 3. TEST WRITE PERMISSIONS
print("\nStep 3: Testing Vault Write...")
try:
    SHEET_ID = "15pD60KIjHB7GNEwlbsYg-STclQ0wKYOA7zkD5oYcaJQ"
    sheet = client.open_by_key(SHEET_ID).sheet1
    
    test_row = ["SYSTEM_CHECK", pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'), "CHECK", 0.0]
    sheet.append_row(test_row)
    print("✅ Successfully wrote a test row to the Vault!")
except gspread.exceptions.SpreadsheetNotFound:
    print("❌ Error: Spreadsheet ID not found. Check the ID in your code.")
except gspread.exceptions.APIError as e:
    print(f"❌ Error: Google API rejected the write. Are you over the 48-hour limit? {e}")
except Exception as e:
    print(f"❌ Unexpected Error: {e}")
