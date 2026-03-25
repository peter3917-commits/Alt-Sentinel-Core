import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import os

# --- 🦅 CLAW'S KEY RECOVERY ---
def get_api_key():
    try:
        # Try Streamlit Secrets first
        if "CP_API_KEY" in st.secrets:
            return st.secrets["CP_API_KEY"]
    except:
        pass
    # Fallback to GitHub/System Environment Variable
    # Using .strip() here ensures no accidental spaces break the Auth
    raw_key = os.getenv("CP_API_KEY", "YOUR_CRYPTOPANIC_API_KEY")
    return raw_key.strip() if raw_key else None

class Claw:
    def __init__(self):
        # 🟢 UPDATED: Using the V2 Developer endpoint as per your instructions
        self.news_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.fng_url = "https://api.alternative.me/fng/"
        self.api_key = get_api_key()

    def get_macro_risk(self):
        """Fetches Fear & Greed Index to establish market-wide risk."""
        try:
            r = requests.get(self.fng_url, timeout=5).json()
            fng_value = int(r['data'][0]['value'])
            return 100 - fng_value # High value = High Risk (Bearish)
        except:
            return 50 

    def get_asset_sentiment(self, ticker):
        """Connects to CryptoPanic V2 to get asset-specific sentiment."""
        if not self.api_key or self.api_key == "YOUR_CRYPTOPANIC_API_KEY":
            return 0.5, "API Key Missing", "System"
            
        params = {
            'auth_token': self.api_key,
            'currencies': ticker,
            'kind': 'news',
            'filter': 'hot',
            'public': 'true'
        }
        
        try:
            # Added a standard User-Agent to ensure the request isn't blocked as a bot
            headers = {'User-Agent': 'Sentinel-Scout-v2'}
            r = requests.get(self.news_url, params=params, headers=headers, timeout=10)
            
            if r.status_code != 200:
                return 0.5, f"V2 Auth Error ({r.status_code})", "CryptoPanic"
                
            data = r.json()
            if not data.get('results'): 
                return 0.5, "No recent news", "N/A"
            
            # Extracting the most recent relevant news
            latest = data['results'][0]
            votes = latest.get('votes', {})
            headline = latest.get('title', "No headline found")
            source = latest.get('domain', "Source")
            
            bullish = votes.get('positive', 0)
            bearish = votes.get('negative', 0)
            
            # Calculation: Ratio of bearish votes to total votes
            sentiment = round(bearish / (bullish + bearish), 2) if (bullish + bearish) > 0 else 0.5
            return sentiment, headline, source
            
        except Exception as e:
            return 0.5, f"V2 Connection Error: {str(e)[:20]}", "Internal"

    def calculate_vibe(self, ticker):
        """Combines Macro Risk and Asset Sentiment into a single score."""
        macro_risk = self.get_macro_risk()
        asset_sentiment, headline, source = self.get_asset_sentiment(ticker)
        
        # Weighted Score: 40% Fear & Greed, 60% Asset Specific News
        total_risk = (macro_risk * 0.4) + (asset_sentiment * 100 * 0.6)
        return round(total_risk, 1), headline, source
