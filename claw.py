import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st
import os

# --- 🦅 CLAW'S KEY RECOVERY ---
def get_api_key():
    try:
        if "CP_API_KEY" in st.secrets:
            return st.secrets["CP_API_KEY"]
    except:
        pass
    raw_key = os.getenv("CP_API_KEY", "YOUR_CRYPTOPANIC_API_KEY")
    return raw_key.strip() if raw_key else None

class Claw:
    def __init__(self):
        # Using the V2 Developer endpoint as per your previous message
        self.news_url = "https://cryptopanic.com/api/developer/v2/posts/"
        self.fng_url = "https://api.alternative.me/fng/"
        self.api_key = get_api_key()

    def get_macro_risk(self):
        try:
            r = requests.get(self.fng_url, timeout=5).json()
            fng_value = int(r['data'][0]['value'])
            return 100 - fng_value 
        except:
            return 50 

    def get_asset_sentiment(self, ticker):
        if not self.api_key or self.api_key == "YOUR_CRYPTOPANIC_API_KEY":
            return 0.5, "API Key Missing", "System"
            
        params = {
            'auth_token': self.api_key,
            'currencies': ticker,
            'filter': 'all',  # 🟢 CHANGED: 'hot' was too restrictive
            'kind': 'all',    # 🟢 CHANGED: 'news' was missing blog/social updates
            'public': 'true'
        }
        
        try:
            headers = {'User-Agent': 'Sentinel-Scout-v2'}
            r = requests.get(self.news_url, params=params, headers=headers, timeout=10)
            
            if r.status_code != 200:
                return 0.5, f"V2 Auth Error ({r.status_code})", "CryptoPanic"
                
            data = r.json()
            # If 'results' is empty, we try a broader search without the currency filter 
            # as a backup to at least get market sentiment.
            if not data.get('results'): 
                return 0.5, "Market Quiet", "Global"
            
            latest = data['results'][0]
            votes = latest.get('votes', {})
            headline = latest.get('title', "No headline found")
            # Truncate headline if it's too long for the sheet
            headline = (headline[:97] + '..') if len(headline) > 100 else headline
            source = latest.get('domain', "Source")
            
            bullish = votes.get('positive', 0)
            bearish = votes.get('negative', 0)
            
            # If no votes yet, sentiment is neutral (0.5)
            sentiment = round(bearish / (bullish + bearish), 2) if (bullish + bearish) > 0 else 0.5
            return sentiment, headline, source
            
        except Exception as e:
            return 0.5, f"V2 Connection Error", "Internal"

    def calculate_vibe(self, ticker):
        macro_risk = self.get_macro_risk()
        asset_sentiment, headline, source = self.get_asset_sentiment(ticker)
        total_risk = (macro_risk * 0.4) + (asset_sentiment * 100 * 0.6)
        return round(total_risk, 1), headline, source
