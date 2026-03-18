import pandas as pd
import pandas_ta as ta

class BrianHarvester:
    def __init__(self, anchor_price, total_budget=200, levels=10, spacing=0.015):
        self.anchor = anchor_price
        self.budget = total_budget
        self.levels = levels
        self.spacing = spacing # 1.5%
        self.wager_per_level = total_budget / levels
        self.active_grid = self._generate_geometric_grid()

    def _generate_geometric_grid(self):
        """Creates the 'Ladder' of buy and sell points."""
        grid = []
        for i in range(1, (self.levels // 2) + 1):
            buy_price = self.anchor * (1 - (self.spacing * i))
            sell_price = self.anchor * (1 + (self.spacing * i))
            grid.append({"type": "BUY", "price": buy_price, "status": "PENDING"})
            grid.append({"type": "SELL", "price": sell_price, "status": "PENDING"})
        return grid

    def check_escalator_logic(self, current_price, rsi_val, last_peak):
        """The Infinity Trailing Logic."""
        # If we hit a sell level but RSI is strong, we HOLD (Trailing)
        if rsi_val > 70:
            # Check for RSI Hook (Downside turn)
            return "HOLD_AND_TRAIL"
        
        # If RSI drops below 65 after being high, or price drops 0.5% from peak
        if current_price < (last_peak * 0.995):
            return "EXECUTE_EXIT"
        
        return "STAY_IN_GRID"

    def should_reset_anchor(self, price_history):
        """Dynamic Anchor: Checks if price settled 2% away for 15 mins."""
        # Logic to check variance in the last 30 intervals (15 mins at 30s heartbeat)
        if len(price_history) < 30: return False
        
        avg_price = sum(price_history) / len(price_history)
        price_diff = abs(avg_price - self.anchor) / self.anchor
        
        # If price moved > 2% and the 'wiggles' are small (0.3% band)
        if price_diff > 0.02 and (max(price_history) - min(price_history)) / avg_price < 0.003:
            return True
        return False
