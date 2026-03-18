import pandas as pd
import os
from datetime import datetime
import numpy as np

class BrianHarvester:
    def __init__(self, anchor_price, tradable_balance, levels=10, spacing=0.03): 
        """
        Brian: The High-Margin Grid Harvester.
        - Spacing: 3% (to ensure profit covers fees/tax).
        - Wager: 2% of the LIVE Tradable Balance per level.
        """
        self.anchor = anchor_price
        self.balance = float(tradable_balance)
        self.levels = levels
        self.spacing = spacing 
        
        # 🎯 THE 2% RULE
        self.wager_per_level = self.balance * 0.02
        self.active_grid = self._generate_geometric_grid()

    def _generate_geometric_grid(self):
        """Generates the BUY/SELL rungs for the Harvester."""
        grid = []
        for i in range(1, (self.levels // 2) + 1):
            # BUYS
            buy_price = self.anchor * (1 - self.spacing) ** i
            grid.append({
                "level": -i, "type": "BUY", "price": round(buy_price, 6), 
                "status": "PENDING", "wager_gbp": round(self.wager_per_level, 2)
            })
            # SELLS
            sell_price = self.anchor * (1 + self.spacing) ** i
            grid.append({
                "level": i, "type": "SELL", "price": round(sell_price, 6), 
                "status": "PENDING", "wager_gbp": round(self.wager_per_level, 2)
            })
        return pd.DataFrame(grid).sort_values('price', ascending=False)

# --- 🚀 GLOBAL UTILITY FUNCTIONS ---

def save_to_log_with_memory(conn, grid_df, sector, anchor):
    """Initializes the grid into the HARVESTER_LOG worksheet."""
    try:
        log_df = grid_df.copy()
        log_df['sector'] = sector.upper()
        log_df['anchor_price'] = anchor
        log_df['timestamp'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cols = ['timestamp', 'sector', 'anchor_price', 'level', 'type', 'price', 'wager_gbp', 'status']
        log_df = log_df[cols]
        
        existing = conn.read(worksheet="HARVESTER_LOG", ttl=0)
        updated = pd.concat([existing, log_df], ignore_index=True)
        conn.update(worksheet="HARVESTER_LOG", data=updated)
        return True
    except Exception as e:
        print(f"❌ Brian Initialization Error: {e}")
        return False

def execute_autonomous_harvest(spreadsheet, sector, current_price):
    """Background worker: Syncs triggers with Ledger and logs Fees to Overheads."""
    try:
        harvest_tab = spreadsheet.worksheet("HARVESTER_LOG")
        ledger_tab = spreadsheet.worksheet("Ledger")
        overheads_tab = spreadsheet.worksheet("Overheads") # 🚀 New Fee Destination

        # 1. 💰 DYNAMIC BALANCE RECONCILIATION
        ledger_data = ledger_tab.get_all_records()
        ledger_df = pd.DataFrame(ledger_data)
        current_balance = float(ledger_df['Tradable_Balance'].iloc[-1]) if 'Tradable_Balance' in ledger_df.columns else 1000.0 

        # 2. Check Grid Triggers
        data = harvest_tab.get_all_records()
        if not data: return False
        df = pd.DataFrame(data); df.columns = [str(c).lower().strip() for c in df.columns]
        
        mask = (df['sector'].str.upper() == sector.upper()) & (df['status'].str.upper() == 'PENDING')
        active_indices = df[mask].index.tolist()

        for idx in active_indices:
            level_price = float(df.at[idx, 'price'])
            order_type = str(df.at[idx, 'type']).upper()
            dynamic_wager = current_balance * 0.02
            
            triggered = False
            if (order_type == "BUY" and current_price <= level_price) or \
               (order_type == "SELL" and current_price >= level_price):
                triggered = True
                
            if triggered:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # --- 💼 LOG EXCHANGE FEE TO OVERHEADS ---
                # Estimated 0.2% fee per trade (Buy or Sell)
                fee_amount = dynamic_wager * 0.002
                fee_entry = [timestamp, f"Exchange Fee: {sector} {order_type}", fee_amount]
                overheads_tab.append_row(fee_entry, value_input_option='USER_ENTERED')
                
                # Update Harvester Log
                harvest_tab.update_cell(idx + 2, df.columns.get_loc('status') + 1, "FILLED")
                
                # Calculate Profit for SELLS
                profit_usd = 0.0
                if order_type == "SELL":
                    anchor = float(df.at[idx, 'anchor_price'])
                    profit_usd = ((level_price / anchor) - 1) * 100

                # Write to Main Ledger
                new_ledger_entry = [timestamp, sector.upper(), f"GRID_{order_type}", 
                                    level_price, dynamic_wager, level_price, profit_usd, 
                                    "CLOSED" if order_type == "SELL" else "OPEN"]
                ledger_tab.append_row(new_ledger_entry, value_input_option='USER_ENTERED')
                
        return True
    except Exception as e:
        print(f"❌ Brian Execution Error: {e}")
        return False
