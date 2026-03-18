import requests

def scout_live_price(coin):
    """
    Vance's (formerly George) improved scouting logic. 
    Connects to the market to fetch real-time USD prices for Alt-Sentinel.
    Now with Multi-Exchange Resilience (Binance Primary / CoinGecko Fallback).
    """
    # 🎯 Internal Mapping: Link Alt-Sentinel names to Market IDs
    # Precision is key here; these assets move in micro-cents.
    coin_map = {
        "XRP": "ripple",
        "XLM": "stellar",
        "HBAR": "hedera-hashgraph"
    }
    
    # Get the correct ID for the API
    market_id = coin_map.get(coin.upper())
    
    if not market_id:
        # If a legacy asset like Bitcoin is passed, Vance will return None 
        # to prevent cross-firm contamination.
        return None

    # --- STRATEGY 1: BINANCE SCOUT (Primary) ---
    # Higher rate limits and faster response times for 2026 markets.
    try:
        binance_symbol = f"{coin.upper()}USDT"
        b_url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
        b_resp = requests.get(b_url, timeout=5)
        if b_resp.status_code == 200:
            price = b_resp.json()['price']
            return float(price)
    except Exception:
        pass # If Binance is throttled, Vance moves to the secondary scout immediately.

    # --- STRATEGY 2: COINGECKO SCOUT (Fallback) ---
    try:
        # Vance calls the simple price endpoint
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={market_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            # Extract the price from the nested JSON
            price = data[market_id]['usd']
            return float(price)
        else:
            return None
            
    except Exception as e:
        # If the scout hits a wall, return None so the Sentinel can skip safely
        return None
