import requests
import pandas as pd
from datetime import datetime, timedelta
import streamlit as st

# --- CONFIG ---
# Pro-tip: Store this in Streamlit Secrets (Settings > Secrets) as "CP_API_KEY"
CP_API_KEY = st.secrets.get("CP_API_KEY", "YOUR_CRYPTOPANIC_API_KEY") 

class Claw:
    def __init__(self):
        self.fng_url = "https://api.alternative.me/fng/"
        self.news_url = "https://cryptopanic.com/api/v1/posts/"

    def get_macro_risk(self):
        try:
            r = requests.get(self.fng_url, timeout=5).json()
            # Fear & Greed is 0-100. 0=Extreme Fear (Risk), 100=Extreme Greed.
            # We invert it: Low F&G value = High Risk.
            fng_value = int(r['data'][0]['value'])
            return 100 - fng_value 
        except:
            return 50 

    def get_asset_sentiment(self, ticker):
        if CP_API_KEY == "YOUR_CRYPTOPANIC_API_KEY":
            return 0.5, "API Key Missing", "System"
            
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
            
            # Sentiment 0 to 1.0 (1.0 = Max Bearish/Risk)
            sentiment = round(bearish / (bullish + bearish), 2) if (bullish + bearish) > 0 else 0.5
            return sentiment, headline, source
        except:
            return 0.5, "Scan Error", "Internal"

    def calculate_vibe(self, ticker):
        macro_risk = self.get_macro_risk()
        asset_sentiment, headline, source = self.get_asset_sentiment(ticker)
        
        # Risk Score: 40% Macro (F&G) + 60% News Sentiment
        # asset_sentiment is 0-1.0, so we * 100 to match macro scale
        total_risk = (macro_risk * 0.4) + (asset_sentiment * 100 * 0.6)
        return round(total_risk, 1), headline, source

# --- 🛰️ LOGGING ENGINE ---
def update_claw_log(conn, ticker="XRP"):
    scout = Claw()
    risk_val, headline, source = scout.calculate_vibe(ticker)
    now = datetime.now()
    
    # FORMATTING FIX: Store as raw number for Jace, add % only for display in Main
    new_entry = pd.DataFrame([{
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "assetrisk_score": float(risk_val), 
        "sentiment_vibe": "BEARISH" if risk_val > 60 else "BULLISH" if risk_val < 40 else "NEUTRAL",
        "top_headline": str(headline)[:100], 
        "source_impact": str(source)
    }])
    
    try:
        # 1. Read existing data
        try:
            existing_df = conn.read(worksheet="Claw_Log", ttl=0)
            if existing_df is not None and not existing_df.empty:
                existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
            else:
                existing_df = pd.DataFrame()
        except:
            existing_df = pd.DataFrame()

        # 2. Add new entry
        combined_df = pd.concat([existing_df, new_entry], ignore_index=True)

        # 3. 🧹 CLEANUP: Last 48 hours
        cutoff = now - timedelta(hours=48)
        combined_df['timestamp'] = pd.to_datetime(combined_df['timestamp'])
        updated_df = combined_df[combined_df['timestamp'] >= cutoff].copy()
        
        # Format back to string for Google Sheets
        updated_df['timestamp'] = updated_df['timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")

        # 4. Write back to sheet
        # Note: Using .write is the standard for the GSheetsConnection update
        conn.write(worksheet="Claw_Log", data=updated_df)
        
        return risk_val
    except Exception as e:
        st.error(f"Claw Log Error: {e}")
        return 50.0
