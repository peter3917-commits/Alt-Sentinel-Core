# --- 🛰️ THE PRECISION ENGINE ---

# D. DATA PREPARATION & SAFE APPEND
if new_records:
    # Prepare only the new rows for insertion (as strings for GSheets)
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
# Instead of clearing the sheet, we only shave off the oldest rows from the top.
try:
    # 1. Fetch current sheet state
    all_values = sheet.get_all_values()
    if len(all_values) > 1:
        headers = all_values[0]
        rows = all_values[1:] # Skip header
        
        # Identify Timestamp column (usually index 1)
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
                # If a row is corrupted or unreadable, mark it for removal
                rows_to_delete += 1 
        
        # 3. Targeted Deletion (Only if old data exists)
        if rows_to_delete > 0:
            # delete_rows(start_index, end_index) 
            # We start at 2 to preserve the header at row 1
            sheet.delete_rows(2, rows_to_delete + 1)
            print(f"🧹 Tidy complete: Removed {rows_to_delete} legacy records (>48h).")
        else:
            print("✨ Vault is already lean. No legacy data to remove.")
            
except Exception as e:
    print(f"⚠️ Tidy-up delayed (Vault remains safe): {e}")
