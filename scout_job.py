import pandas as pd
import vance, kael, jace, piper, brian
from streamlit_gsheets import GSheetsConnection
import os

# --- SILENT SCOUT CONFIG (No Streamlit UI allowed here) ---
ASSETS = ["XRP", "XLM", "HBAR"]

def run_background_scout():
    print("🛰️ Vance: Commencing background scout mission...")
    
    # Use a dummy class to satisfy the GSheets connection without a UI
    class MockStreamlit:
        def secrets(self): return os.environ
    
    # Logic to fetch price and update Google Sheets
    for coin in ASSETS:
        price = vance.scout_live_price(coin)
        if price:
            print(f"✅ {coin} spotted at ${price:,.6f}")
            # Here Vance writes to the 'Vault' sheet so the Main App can see it
            vance.log_to_vault(coin, price) 

if __name__ == "__main__":
    run_background_scout()
