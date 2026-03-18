# --- 🛰️ INITIALIZATION ---
import vance
from datetime import datetime, timedelta
import pandas as pd

new_records = []  
ASSETS = ["XRP", "XLM", "HBAR"]

# 🚀 THE COLLECTION
for coin in ASSETS:
    try:
        price = vance.scout_live_price(coin)
        if price:
            new_records.append({
                "staff": "Vance", # Lowercase to match main.py logic
                "timestamp": datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                "asset": coin.upper(),
                "price_usd": price
            })
            print(f"🛰️ Scouted {coin}: ${price}")
        else:
            print(f"⚠️ Vance returned no price for {coin} (Possible API Rate Limit)")
    except Exception as e:
        print(f"❌ Failed to scout {coin}: {e}")

# --- 🛰️ THE PRECISION ENGINE ---

if new_records:
    # Match the exact lowercase columns main.py expects
    rows_to_append = [
        [r["staff"], r["timestamp"], r["asset"], r["price_usd"]]
        for r in new_records
    ]
    
    try:
        sheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        print(f"✅ Vault updated: +{len(rows_to_append)} records.")
        
        # --- 🛡️ SAFETY BRAKE TIDY ---
        # ONLY delete old records IF we successfully added new ones today.
        all_values = sheet.get_all_values()
        if len(all_values) > 10: # Keep at least a small buffer
            headers = [h.lower().strip() for h in all_values[0]]
            rows = all_values[1:]
            
            ts_idx = headers.index("timestamp") if "timestamp" in headers else 1
            cutoff = datetime.utcnow() - timedelta(hours=48)
            
            rows_to_delete = 0
            for row in rows:
                try:
                    row_ts = pd.to_datetime(row[ts_idx])
                    if row_ts < cutoff:
                        rows_to_delete += 1
                    else:
                        break 
                except:
                    # Only delete if it's actually empty or nonsense
                    if not row[ts_idx]: rows_to_delete += 1
                    else: break
            
            if rows_to_delete > 0:
                sheet.delete_rows(2, rows_to_delete + 1)
                print(f"🧹 Removed {rows_to_delete} old records.")
    except Exception as e:
        print(f"⚠️ Vault update failed: {e}")
else:
    print("🛑 API FETCH FAILED: Skipping Tidy-up to protect existing Vault data.")
