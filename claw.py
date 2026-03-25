import requests
import time

# --- CONFIG ---
# Get a free API Key at https://cryptopanic.com/developers/api/
CP_API_KEY = "YOUR_CRYPTOPANIC_API_KEY" 

class Claw:
    def __init__(self):
        self.fng_url = "https://api.alternative.me/fng/"
        self.news_url = "https://cryptopanic.com/api/v1/posts/"

    def get_macro_risk(self):
        """Fetches the 0-100 Fear & Greed Index score."""
        try:
            r = requests.get(self.fng_url, timeout=5).json()
            return int(r['data'][0]['value'])
        except:
            return 50 # Neutral default

    def get_asset_sentiment(self, ticker):
        """
        Scans news for specific tickers. 
        Returns a simplified 'Risk Multiplier' (0.5 to 1.5).
        """
        params = {
            'auth_token': CP_API_KEY,
            'currencies': ticker,
            'kind': 'news',
            'filter': 'hot'
        }
        try:
            r = requests.get(self.news_url, params=params, timeout=5).json()
            votes = r['results'][0]['votes']
            # Logic: More 'bearish' votes = Higher Risk %
            bullish = votes.get('positive', 0)
            bearish = votes.get('negative', 0)
            
            if (bullish + bearish) == 0: return 0 # No news is neutral
            return round(bearish / (bullish + bearish), 2)
        except:
            return 0.5 # Default to middle-ground risk

    def calculate_vibe(self, ticker):
        macro = self.get_macro_risk()       # 0-100
        asset_risk = self.get_asset_sentiment(ticker) # 0-1
        
        # Weighted Risk Formula: 40% Macro + 60% Specific News
        # We invert Macro (because 100 Greed is actually 'Riskier' for buying)
        total_risk = (macro * 0.4) + (asset_risk * 100 * 0.6)
        
        return round(total_risk, 1)
