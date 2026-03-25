import requests
import os
import streamlit as st
import time

# --- 🦅 CLAW'S KEY RECOVERY ---
def get_api_key():
    try:
        if "CP_API_KEY" in st.secrets:
            return st.secrets["CP_API_KEY"]
    except:
        pass
    # Get from environment and clean it
    key = os.getenv("CP_API_KEY")
    return key.strip() if key else None

class Claw:
    def __init__(self):
        # 🟢 EXACT URL FROM YOUR CRYPTOPANIC DASHBOARD
        self.base_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.fng_url = "https://api.alternative.me/fng/"
        self.api_key = get_api_key()

    def get_macro_risk(self):
        try:
            r = requests.get(self.fng_url, timeout=5).json()
            return 100 - int(r['data'][0]['value'])
        except:
            return 50 

    def get_asset_sentiment(self, ticker):
        if not self.api_key:
            return 0.5, "API Key Missing", "System"
            
        # 🟢 SIMPLIFIED PARAMETERS: Using only what is strictly necessary
        params = {
            'auth_token': self.api_key,
            'currencies': ticker,
            'public': 'true'
        }
        
        try:
            # Add a small delay so we don't trigger the 5 req/sec limit
            time.sleep(1) 
            
            response = requests.get(self.base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                if results:
                    latest = results[0]
                    votes = latest.get('votes', {})
                    pos, neg = votes.get('positive', 0), votes.get('negative', 0)
                    sentiment = round(neg / (pos + neg), 2) if (pos + neg) > 0 else 0.5
                    return sentiment, latest.get('title', "News Found"), latest.get('domain', "Source")
                return 0.5, "No recent news", "N/A"
            
            # This captures the 500 error and tells us it's a server-side rejection
            return 0.5, f"V2 Server Error ({response.status_code})", "CryptoPanic"
            
        except Exception as e:
            return 0.5, f"Connection Failed", "Internal"

    def calculate_vibe(self, ticker):
        macro_risk = self.get_macro_risk()
        asset_sentiment, headline, source = self.get_asset_sentiment(ticker)
        # 40% Fear/Greed + 60% Asset News
        score = (macro_risk * 0.4) + (asset_sentiment * 100 * 0.6)
        return round(score, 1), headline, source
