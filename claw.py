import requests
import time

class Claw:
    def __init__(self):
        """
        Claw 2.1: Macro-Only Evolution.
        Decommissioned CryptoPanic API to ensure 100% sustainability.
        Uses the global Fear & Greed Index as the primary risk governor.
        """
        # 🟢 SUSTAINABLE MACRO SOURCE: Free & Robust
        self.fng_url = "https://api.alternative.me/fng/"

    def get_macro_risk(self):
        """
        Fetches the global 'Market Vibe'.
        Inverts the index: 100 (Extreme Greed) = 0 Risk; 0 (Extreme Fear) = 100 Risk.
        """
        try:
            # Add a brief delay to prevent API rate-limiting during rapid pings
            time.sleep(0.5)
            response = requests.get(self.fng_url, timeout=5).json()
            
            # The API returns 0-100 (Fear to Greed). 
            # We subtract from 100 because Jace treats high numbers as 'Risk to be avoided'.
            fng_value = int(response['data'][0]['value'])
            return 100 - fng_value
        except Exception:
            # Institutional Fallback: Assume neutral risk if the connection fails.
            return 50 

    def calculate_vibe(self, ticker):
        """
        Calculates the Firm's Risk Multiplier.
        Maintains the (Score, Headline, Source) signature to prevent Matrix crashes.
        """
        macro_risk = self.get_macro_risk()
        
        # We provide a standardized status for the Ledger and UI consistency.
        headline = f"Macro Risk Protocol Active for {ticker}"
        source = "Alternative.me (F&G)"
        
        # Current logic puts 100% weight on Macro Risk.
        score = float(macro_risk)
        
        return round(score, 1), headline, source
