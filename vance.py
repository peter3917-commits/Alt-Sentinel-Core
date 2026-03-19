import requests
from datetime import datetime

def scout_live_price(coin):
    """
    Vance's Standard Scout: Real-time price fetch.
    Binance Primary / CoinGecko Fallback.
    """
    # 🎯 Internal Mapping: Link Alt-Sentinel names to Market IDs
    coin_map = {
        "XRP": "ripple",
        "XLM": "stellar",
        "HBAR": "hedera-hashgraph"
    }
    
    market_id = coin_map.get(coin.upper())
    
    if not market_id:
        return None

    # --- STRATEGY 1: BINANCE SCOUT (Primary) ---
    try:
        binance_symbol = f"{coin.upper()}USDT"
        b_url = f"https://api.binance.com/api/v3/ticker/price?symbol={binance_symbol}"
        b_resp = requests.get(b_url, timeout=5)
        if b_resp.status_code == 200:
            price = b_resp.json()['price']
            return float(price)
    except Exception:
        pass 

    # --- STRATEGY 2: COINGECKO SCOUT (Fallback) ---
    try:
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={market_id}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            price = data[market_id]['usd']
            return float(price)
        else:
            return None
            
    except Exception as e:
        return None

def scout_historic_price(coin, timestamp_ms):
    """
    🚀 NEW: Vance's Point-in-Time Scout.
    Fetches the price for a specific historical timestamp (Unix Milliseconds).
    Used to fill gaps in the 'Vault' Google Form every 5 minutes.
    """
    try:
        symbol = f"{coin.upper()}USDT"
        # Binance 'klines' (candles) starts at 'startTime'. 
        # interval=1m gets us the exact minute requested.
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1m&startTime={timestamp_ms}&limit=1"
        resp = requests.get(url, timeout=5)
        
        if resp.status_code == 200:
            data = resp.json()
            if data:
                # Position [4] is the Closing price for that specific minute.
                return float(data[0][4])
    except Exception as e:
        print(f"❌ Vance Historic Lookup Error: {e}")
    
    return None
