import requests
import pandas as pd
from datetime import datetime

# --- CONFIG ---
CP_API_KEY = "YOUR_CRYPTOPANIC_API_KEY" 

class Claw:
    def __init__(self):
        self.fng_url = "https://api.alternative.me/fng/"
        self.news_url = "https://cryptopanic.com/api/v1/posts/"

    def get_macro_risk(self):
        try:
            r = requests.get(self.fng_url, timeout=5).json()
            return int(r['data'][0]['value'])
        except:
            return 50 

    def get_asset_sentiment(self, ticker):
        params = {
            'auth_token': CP_API_KEY,
            'currencies': ticker,
            'kind': 'news',
            'filter': 'hot'
        }
        try:
            r = requests.get(self.news_url, params=params, timeout=5).json()
            votes = r['results'][0]['votes']
            bullish = votes.get('positive', 0)
            bearish = votes.get('negative', 0)
            if (bullish + bearish) == 0: return 0.5 
            return round(bearish / (bullish + bearish), 2)
        except:
            return 0.5 

    def calculate_vibe(self, ticker):
        macro = self.get_macro_risk()       
        asset_risk = self.get_asset_sentiment(ticker) 
        total_risk = (macro * 0.4) + (asset_risk * 100 * 0.6)
        return round(total_risk, 1)

# --- 🛰️ NEW: THE WRITING FUNCTION ---
def update_claw_log(conn, ticker="XRP"):
    """
    Surgical Update: This takes the calculated risk and 
    writes it to the 'Claw_Log' tab in your Google Sheet.
    """
    scout = Claw()
    risk_score = scout.calculate_vibe(ticker)
    
    # Create the row for the Google Sheet
    new_entry = pd.DataFrame([{
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "risk_score": f"{risk_score}%",
        "note": f"Automated scan for {ticker}"
    }])
    
    try:
        # 1. Read existing log from the tab named 'Claw_Log'
        existing_df = conn.read(worksheet="Claw_Log")
        
        # 2. Append the new risk score
        updated_df = pd.concat([existing_df, new_entry], ignore_index=True)
        
        # 3. Write back (keep last 100 rows to prevent sheet bloat)
        conn.update(worksheet="Claw_Log", data=updated_df.tail(100))
        
        print(f"🦅 Claw: Market Risk logged at {risk_score}%")
        return risk_score
    except Exception as e:
        print(f"⚠️ Claw Logging Error: {e}")
        return 50.0
