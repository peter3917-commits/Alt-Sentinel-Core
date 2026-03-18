# --- 🛰️ INITIALIZATION (FIXES THE CRASH) ---
new_records = []  # Prevents NameError
ASSETS = ["XRP", "XLM", "HBAR"]

# 🚀 THE MISSING COLLECTION (This fills the list for Section D)
for coin in ASSETS:
    try:
        price = vance.scout_live_price(coin)
        if price:
            new_records.append({
                "Staff": "Vance",
                "Timestamp": datetime.utcnow(),
                "Asset": coin,
                "Price_Usd": price
            })
            print(f"🛰️ Scouted {coin}: ${price}")
    except Exception as e:
        print(f"❌ Failed to scout {coin}: {e}")

# --- 🛰️ THE PRECISION ENGINE ---

# D. DATA PREPARATION & SAFE APPEND
if new_records:
    # Prepare rows matching your Vault exactly: Staff, Timestamp, Asset, Price_Usd
    rows_to_append = [
        [r["Staff"], r["Timestamp"].strftime('%Y-%m-%d %H:%M:%S'), r["Asset"], r["Price_Usd"]]
        for r in new_records
    ]
    
    try:
        # PURE APPEND: This adds to the bottom and NEVER wipes the sheet.
        sheet.append_rows(rows_to_append, value_input_option='USER_ENTERED')
        print(f"✅ Vault updated: +{len(rows_to_append)} new records added to bottom.")
    except Exception as e:
        print(f"⚠️ Vault append failed: {e}")

# E. PRECISION TIDY (48-HOUR CUTOFF)
# Only shaves oldest rows from the top if they are over 48 hours old.
try:
    # 1. Fetch current sheet state
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        headers = all_values[0]
        rows = all_values[1:] # Skip header
        
        # Identify Timestamp column
        ts_idx = headers.index("Timestamp") if "Timestamp" in headers else 1
        cutoff = datetime.utcnow() - timedelta(hours=48)
        
        # 2. Count how many rows at the TOP are older than 48 hours
        rows_to_delete = 0
        for row in rows:
            try:
                row_ts = pd.to_datetime(row[ts_idx])
                if row_ts < cutoff:
                    rows_to_delete += 1
                else:
                    break # Stop once we reach data within the 48h window
            except:
                # If a row is corrupted, mark for removal to keep sheet clean
                rows_to_delete += 1 
        
        # 3. Targeted Deletion (Only if old data exists)
        if rows_to_delete > 0:
            # We start at row 2 to preserve the header at row 1
            sheet.delete_rows(2, rows_to_delete + 1)
            print(f"🧹 Tidy complete: Removed {rows_to_delete} legacy records (>48h).")
        else:
            print("✨ Vault is already lean. No legacy data to remove.")
            
except Exception as e:
    print(f"⚠️ Tidy-up delayed (Vault remains safe): {e}")
