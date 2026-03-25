import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import os

# --- 🦅 CLAW'S KEY RECOVERY ---
def get_api_key():
    try:
        # Try Streamlit Secrets (for the web dashboard)
        if "CP_API_KEY" in st.secrets:
            return st.secrets["CP_API_KEY"]
    except:
        pass
    # Fallback to GitHub/System Environment Variable
    return os.getenv("CP_API_KEY", "YOUR_CRYPTOPANIC_API_KEY")

CP_API_KEY = get_api_key()

class Claw:
    def __init__(self):
        self.fng_url = "https://api.alternative.me/fng/"
        self.news_url = "https://cryptopanic.com/api/v1/posts/"

    def get_macro_risk(self):
        try:
            r = requests.get(self.fng_url, timeout=5).json()
            fng_value = int(r['data'][0]['value'])
            return 100 - fng_value 
        except:
            return 50 

    def get_asset_sentiment(self, ticker):
        if not CP_API_KEY or CP_API_KEY == "YOUR_CRYPTOPANIC_API_KEY":
            return 0.5, "API Key Missing", "System"
            
        params = {
            'auth_token': CP_API_KEY,
            'currencies': ticker,
            'kind': 'news',
            'filter': 'hot'
        }
        try:
            r = requests.get(self.news_url, params=params, timeout=5)
            if r.status_code != 200:
                return 0.5, f"Auth Error ({r.status_code})", "CryptoPanic"
                
            data = r.json()
            if not data.get('results'): 
                return 0.5, "No recent news", "N/A"
            
            latest = data['results'][0]
            votes = latest.get('votes', {})
            headline = latest.get('title', "No headline found")
            source = latest.get('domain', "Unknown Source")
            
            bullish = votes.get('positive', 0)
            bearish = votes.get('negative', 0)
            
            sentiment = round(bearish / (bullish + bearish), 2) if (bullish + bearish) > 0 else 0.5
            return sentiment, headline, source
        except Exception as e:
            print(f"DEBUG: Connection error for {ticker}: {e}")
            return 0.5, "Connection Error", "Internal"

    def calculate_vibe(self, ticker):
        macro_risk = self.get_macro_risk()
        asset_sentiment, headline, source = self.get_asset_sentiment(ticker)
        total_risk = (macro_risk * 0.4) + (asset_sentiment * 100 * 0.6)
        return round(total_risk, 1), headline, source
