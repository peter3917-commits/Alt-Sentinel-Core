import sys
import vance
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd

def log(msg):
    print(f">>> {msg}")
    sys.stdout.flush() # Forces the terminal to show the text instantly

log("STATION CHECK STARTING...")

# 1. TEST VANCE (The most likely 'hang' point)
log("Attempting to reach Vance...")
try:
    price = vance.scout_live_price("XRP")
    log(f"Vance Response: {price}")
except Exception as e:
    log(f"Vance crashed: {e}")

# 2. TEST AUTH
log("Opening credentials file...")
try:
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_file("creds.json", scopes=scope)
    client = gspread.authorize(creds)
    log("Auth Success.")
except Exception as e:
    log(f"Auth Failure: {e}")

# 3. TEST SHEET
log("Connecting to Sheet ID...")
try:
    SHEET_ID = "15pD60KIjHB7GNEwlbsYg-STclQ0wKYOA7zkD5oYcaJQ"
    sheet = client.open_by_key(SHEET_ID).sheet1
    log(f"Connected to sheet: {sheet.title}")
    
    log("Sending test row...")
    sheet.append_row(["DEBUG", pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S'), "CHECK", 0.0])
    log("✅ WRITE SUCCESSFUL! Check the Google Sheet now.")
except Exception as e:
    log(f"Sheet error: {e}")

log("STATION CHECK COMPLETE.")
