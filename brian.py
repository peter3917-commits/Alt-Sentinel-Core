import pandas as pd
import pandas_ta as ta
import numpy as np
import streamlit as st
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

class BrianHarvester:
    def __init__(self, anchor_price, tradable_balance, levels=10, spacing=0.015):
        """
        Brian.py: Updated for Dynamic Liquidity.
        - Wager: Now 2% of Tradable Balance per level.
        """
        self.anchor = anchor_price
        self.balance = tradable_balance
        self.levels = levels
        self.spacing = spacing 
        
        # 🎯 THE 2% RULE
        self.wager_per_level = float(self.balance) * 0.02
        
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
    Calculates dynamic balance from Ledger and executes trades.
    """
    try:
        harvest_tab = spreadsheet.worksheet("HARVESTER_LOG")
        ledger_tab = spreadsheet.worksheet("Ledger")

        # 1. 💰 DYNAMIC BALANCE CALCULATION
        # Brian reads the Ledger to find out how much 'Tradable_Balance' is left.
        ledger_data = ledger_tab.get_all_records()
        ledger_df = pd.DataFrame(ledger_data)
        
        # Look for the last known Tradable_Balance in your Ledger columns
        # If your Ledger doesn't have a balance column, we assume a base (e.g., £1000)
        # or calculate it: Seed - (All Active Wagers)
        if 'Tradable_Balance' in ledger_df.columns:
            current_balance = float(ledger_df['Tradable_Balance'].iloc[-1])
        else:
            # Fallback if Piper hasn't calculated a balance column yet
            current_balance = 1000.0 

        # 2. Check Grid Triggers
        data = harvest_tab.get_all_records()
        if not data: return False

        df = pd.DataFrame(data)
        df.columns = [str(c).lower().strip() for c in df.columns]
        
        mask = (df['sector'].str.upper() == sector.upper()) & (df['status'].str.upper() == 'PENDING')
        active_indices = df[mask].index.tolist()

        for idx in active_indices:
            level_price = float(df.at[idx, 'price'])
            order_type = str(df.at[idx, 'type']).upper()
            
            # 🎯 APPLY THE 2% WAGER BASED ON LIVE BALANCE
            dynamic_wager = current_balance * 0.02
            
            triggered = False
            if order_type == "BUY" and current_price <= level_price:
                triggered = True
            elif order_type == "SELL" and current_price >= level_price:
                triggered = True
                
            if triggered:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # Update Harvester Log
                row_num = idx + 2 
                harvest_tab.update_cell(row_num, df.columns.get_loc('status') + 1, "FILLED")
                
                # Write to Main Ledger
                profit_pct = 0.0
                if order_type == "SELL":
                    anchor = float(df.at[idx, 'anchor_price'])
                    profit_pct = ((level_price / anchor) - 1) * 100

                new_ledger_entry = [
                    timestamp, 
                    sector.upper(), 
                    f"GRID_{order_type}", 
                    level_price, 
                    dynamic_wager, 
                    level_price, 
                    profit_pct, 
                    "CLOSED" if order_type == "SELL" else "OPEN"
                ]
                ledger_tab.append_row(new_ledger_entry, value_input_option='USER_ENTERED')
                print(f"🏛️ LEDGER UPDATED: {sector} {order_type} for £{dynamic_wager:.2f}")

        return True
    except Exception as e:
        print(f"❌ Brian's Ledger Reporting Error: {e}")
        return False
