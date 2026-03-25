import requests
import pandas as pd
from datetime import datetime, timedelta

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
            if not r.get('results'): return 0.5, "No recent news", "N/A"
            
            latest = r['results'][0]
            votes = latest.get('votes', {})
            headline = latest.get('title', "No headline found")
            source = latest.get('domain', "Unknown Source")
            
            bullish = votes.get('positive', 0)
            bearish = votes.get('negative', 0)
            
            sentiment = round(bearish / (bullish + bearish), 2) if (bullish + bearish) > 0 else 0.5
            return sentiment, headline, source
        except:
            return 0.5, "Scan Error", "Internal"

    def calculate_vibe(self, ticker):
        macro = self.get_macro_risk()
        asset_risk, headline, source = self.get_asset_sentiment(ticker)
        
        # Risk Score: 40% Macro + 60% News Sentiment
        total_risk = (macro * 0.4) + (asset_risk * 100 * 0.6)
        return round(total_risk, 1), headline, source

# --- 🛰️ LOGGING ENGINE ---
def update_claw_log(conn, ticker="XRP"):
    scout = Claw()
    risk_val, headline, source = scout.calculate_vibe(ticker)
    now = datetime.now()
    
    # New entry to add
    new_entry = pd.DataFrame([{
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "assetrisk_score": f"{risk_val}%",
        "sentiment_vibe": "BEARISH" if risk_val > 60 else "BULLISH" if risk_val < 40 else "NEUTRAL",
        "top_headline": headline[:100], 
        "source_impact": source
    }])
    
    try:
        # 1. Read existing data
        try:
            existing_df = conn.read(worksheet="Claw_Log")
            # Ensure timestamp is datetime for filtering
            existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
        except:
            existing_df = pd.DataFrame(columns=["timestamp", "assetrisk_score", "sentiment_vibe", "top_headline", "source_impact"])

        # 2. Add new entry
        combined_df = pd.concat([existing_df, new_entry], ignore_index=True)

        # 3. 🧹 CLEANUP: Filter for records from the last 48 hours ONLY
        cutoff = now - timedelta(hours=48)
        # Convert timestamp back to datetime (just in case) and filter
        combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
        updated_df = combined_df[combined_df['timestamp'] >= cutoff].copy()
        
        # Format timestamp back to string for neat Google Sheets display
        updated_df['timestamp'] = updated_df['timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")

        # 4. Write back to sheet (Overwrites with the fresh 48-hour window)
        conn.update(worksheet="Claw_Log", data=updated_df)
        
        print(f"🦅 Claw Cleanup: Log restricted to last 48 hours. Current records: {len(updated_df)}")
        return risk_val
    except Exception as e:
        print(f"Claw Write/Cleanup Error: {e}")
        return 50.0
