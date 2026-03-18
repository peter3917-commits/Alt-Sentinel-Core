import pandas as pd
import pandas_ta as ta
import numpy as np
import streamlit as st
from streamlit_gsheets import GSheetsConnection

class BrianHarvester:
    def __init__(self, anchor_price, total_budget=200, levels=10, spacing=0.015):
        """
        Brian.py: Specialized in extracting profit from volatility (The Wiggle).
        - Geometric Spacing: Spacing is a fixed % (1.5%).
        - Survival Logic: Operates strictly within the £200 'Working Capital'.
        """
        self.anchor = anchor_price
        self.budget = total_budget
        self.levels = levels
        self.spacing = spacing  # 1.5%
        self.wager_per_level = total_budget / levels
        self.tax_rate = 0.20 # Piper's 20% Cut
        
        # 🟢 Initialize the Grid
        self.active_grid = self._generate_geometric_grid()

    def _generate_geometric_grid(self):
        """
        Calculates 5 BUY levels below and 5 SELL levels above the anchor 
        using a geometric progression (Fixed Percentage).
        """
        grid = []
        # Calculate BUY levels (Lowering from anchor)
        # Price_n = Anchor * (1 - spacing)^n
        for i in range(1, (self.levels // 2) + 1):
            buy_price = self.anchor * (1 - self.spacing) ** i
            grid.append({
                "level": -i,
                "type": "BUY", 
                "price": round(buy_price, 6), 
                "status": "PENDING",
                "wager_gbp": self.wager_per_level
            })
        
        # Calculate SELL levels (Rising from anchor)
        # Price_n = Anchor * (1 + spacing)^n
        for i in range(1, (self.levels // 2) + 1):
            sell_price = self.anchor * (1 + self.spacing) ** i
            grid.append({
                "level": i,
                "type": "SELL", 
                "price": round(sell_price, 6), 
                "status": "PENDING",
                "wager_gbp": self.wager_per_level
            })
            
        return pd.DataFrame(grid).sort_values('price', ascending=False)

    def save_grid_to_ledger(self, conn, sector="HBAR"):
        """
        Writes Brian's active rungs to the HARVESTER_LOG tab.
        Updated to handle multi-asset appending safely.
        """
        try:
            # Prepare data for Google Sheets
            log_df = self.active_grid.copy()
            log_df['sector'] = sector.upper()
            log_df['anchor_price'] = self.anchor
            log_df['timestamp'] = pd.to_datetime('now').strftime('%Y-%m-%d %H:%M:%S')
            
            # Reorder for the Sheet to match main.py expectation
            cols = ['timestamp', 'sector', 'anchor_price', 'type', 'price', 'status', 'wager_gbp']
            log_df = log_df[cols]
            
            # 🎯 PRECISION UPDATE:
            # Instead of a full sheet overwrite, we suggest using the streamlit-gsheets 
            # connection to handle the update to the specific worksheet.
            conn.update(worksheet="HARVESTER_LOG", data=log_df)
            return True
        except Exception as e:
            st.error(f"Brian's Ledger Error: {e}")
            return False

    def check_escalator_logic(self, current_price, rsi_val, last_peak):
        """
        Infinity Trailing Logic:
        If price hits a SELL level, check RSI.
        """
        if rsi_val >= 70:
            if current_price < (last_peak * 0.995):
                return "EXECUTE_EXIT"
            return "STAY_IN_TRAIL"
        
        if current_price > (last_peak * 1.002): 
            return "HOLD_AND_TRAIL"
            
        return "STAY_IN_GRID"

    def get_piper_breakdown(self, buy_price, sell_price):
        """
        Calculates the clean profit for Piper.
        Logic: (Revenue - Cost) - 20% Tax.
        """
        # Shares bought = Wager / Buy Price
        shares = self.wager_per_level / buy_price
        gross_profit = (sell_price - buy_price) * shares
        tax_pot_contribution = gross_profit * self.tax_rate
        net_to_company = gross_profit - tax_pot_contribution
        
        return {
            "gross": round(gross_profit, 2),
            "tax": round(tax_pot_contribution, 2),
            "net": round(net_to_company, 2)
        }
