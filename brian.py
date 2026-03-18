import pandas as pd
import pandas_ta as ta
import numpy as np
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

class BrianHarvester:
    def __init__(self, anchor_price, total_budget=200, levels=10, spacing=0.015):
        self.anchor = anchor_price
        self.budget = total_budget
        self.levels = levels
        self.spacing = spacing 
        self.wager_per_level = total_budget / levels
        self.tax_rate = 0.20 
        self.active_grid = self._generate_geometric_grid()

    def _generate_geometric_grid(self):
        grid = []
        for i in range(1, (self.levels // 2) + 1):
            buy_price = self.anchor * (1 - self.spacing) ** i
            grid.append({
                "level": -i, "type": "BUY", "price": round(buy_price, 6), 
                "status": "PENDING", "wager_gbp": self.wager_per_level
            })
        for i in range(1, (self.levels // 2) + 1):
            sell_price = self.anchor * (1 + self.spacing) ** i
            grid.append({
                "level": i, "type": "SELL", "price": round(sell_price, 6), 
                "status": "PENDING", "wager_gbp": self.wager_per_level
            })
        return pd.DataFrame(grid).sort_values('price', ascending=False)

# --- 🚀 GLOBAL UTILITY FUNCTIONS ---

def execute_autonomous_harvest(spreadsheet, sector, current_price):
    """
    Background worker for scout_job.py.
    Now reports to both HARVESTER_LOG and the main LEDGER.
    """
    try:
        # 1. Access the Tabs
        harvest_tab = spreadsheet.worksheet("HARVESTER_LOG")
        try:
            ledger_tab = spreadsheet.worksheet("Ledger") # Matches your Ledger tab name
        except:
            ledger_tab = spreadsheet.get_worksheet(1) # Fallback to second tab if name differs

        data = harvest_tab.get_all_records()
        if not data: return False

        df = pd.DataFrame(data)
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        mask = (df['sector'].str.upper() == sector.upper()) & (df['status'].str.upper() == 'PENDING')
        active_indices = df[mask].index.tolist()

        for idx in active_indices:
            level_price = float(df.at[idx, 'price'])
            order_type = str(df.at[idx, 'type']).upper()
            wager = float(df.at[idx, 'wager_gbp'])
            
            triggered = False
            if order_type == "BUY" and current_price <= level_price:
                triggered = True
            elif order_type == "SELL" and current_price >= level_price:
                triggered = True
                
            if triggered:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # A. Update Harvester Log (The local grid state)
                row_num = idx + 2 
                status_col = df.columns.get_loc('status') + 1
                harvest_tab.update_cell(row_num, status_col, "FILLED")
                
                # B. Write to Main Ledger (The permanent firm record)
                # Format: Timestamp, Asset, Type, Price, Wager, Result (HighWater), Profit, Result Clean
                # Note: For SELLs, Brian assumes a successful harvest from the anchor.
                profit_pct = 0.0
                if order_type == "SELL":
                    # Simple grid profit calculation: (Price / Anchor) - 1
                    anchor = float(df.at[idx, 'anchor_price'])
                    profit_pct = ((level_price / anchor) - 1) * 100

                new_ledger_entry = [
                    timestamp, 
                    sector.upper(), 
                    f"GRID_{order_type}", 
                    level_price, 
                    wager, 
                    level_price, # Result/Peak
                    profit_pct, 
                    "CLOSED" if order_type == "SELL" else "OPEN"
                ]
                ledger_tab.append_row(new_ledger_entry, value_input_option='USER_ENTERED')
                
                print(f"🏛️ LEDGER UPDATED: Brian recorded {sector} {order_type} at ${level_price}")

        return True
    except Exception as e:
        print(f"❌ Brian's Ledger Reporting Error: {e}")
        return False

# ... (keep save_to_log_with_memory as it was)
