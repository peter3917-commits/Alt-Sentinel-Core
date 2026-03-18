import pandas as pd
import pandas_ta as ta
import numpy as np

class BrianHarvester:
    def __init__(self, anchor_price, total_budget=200, levels=10, spacing=0.015):
        """
        Brian.py: Specialized in extracting profit from volatility (The Wiggle).
        - Geometric Spacing: Spacing is a fixed % (1.5%), not a fixed dollar amount.
        - Survival Logic: Operates strictly within the £200 'Working Capital'.
        """
        self.anchor = anchor_price
        self.budget = total_budget
        self.levels = levels
        self.spacing = spacing  # e.g., 0.015 = 1.5%
        self.wager_per_level = total_budget / levels
        self.tax_rate = 0.20 # Piper's 20% Cut
        
        # Initialize the Grid
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
            
        # Return as sorted DataFrame for the UI to display clearly
        return pd.DataFrame(grid).sort_values('price', ascending=False)

    def check_escalator_logic(self, current_price, rsi_val, last_peak):
        """
        Infinity Trailing Logic:
        If price hits a SELL level, check RSI. If RSI < 70 (Strong momentum), 
        HOLD and let the profit build.
        """
        # 1. Check if we are in the 'Overbought' danger zone
        if rsi_val >= 70:
            # Momentum is peaking; look for the "Hook" (0.5% drop from the local peak)
            if current_price < (last_peak * 0.995):
                return "EXECUTE_EXIT"
            return "STAY_IN_TRAIL"
        
        # 2. If RSI is healthy (< 70), keep riding the move
        if current_price > (last_peak * 1.002): # New high detected
            return "HOLD_AND_TRAIL"
            
        return "STAY_IN_GRID"

    def should_reset_anchor(self, price_history):
        """
        Dynamic Anchor: Checks if price settled 2% away for 15 mins.
        Requires 30 data points (assuming a 30s heartbeat).
        """
        if len(price_history) < 30:
            return False
            
        # Analyze the last 15 minutes of 'wiggles'
        recent_window = price_history[-30:]
        avg_price = np.mean(recent_window)
        
        # Metric 1: Distance from current anchor
        price_drift = abs(avg_price - self.anchor) / self.anchor
        
        # Metric 2: Stability (Are we 'leveling out'?)
        # Calculate the spread (max-min) as a % of the average
        volatility_band = (max(recent_window) - min(recent_window)) / avg_price
        
        # If moved > 2% and stabilized in a tight 0.3% band
        if price_drift > 0.02 and volatility_band < 0.003:
            return True
        return False

    def get_piper_breakdown(self, buy_price, sell_price):
        """
        Calculates the clean profit for Piper.
        Logic: (Revenue - Cost) - 20% Tax.
        """
        gross_profit = (sell_price - buy_price) * (self.wager_per_level / buy_price)
        tax_pot_contribution = gross_profit * self.tax_rate
        net_to_company = gross_profit - tax_pot_contribution
        
        return {
            "gross": round(gross_profit, 2),
            "tax": round(tax_pot_contribution, 2),
            "net": round(net_to_company, 2)
        }
