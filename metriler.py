class PerformanceAnalysis:
    def __init__(self, returns):
        self.returns = returns

    def calculate_roi(self):
        total_return = sum(self.returns)
        roi = total_return / len(self.returns)
        return roi

    def calculate_sharpe_ratio(self, risk_free_rate=0.01):
        excess_returns = [r - risk_free_rate for r in self.returns]
        sharpe_ratio = sum(excess_returns) / (len(excess_returns) ** 0.5)
        return sharpe_ratio

    def calculate_max_drawdown(self):
        max_drawdown = 0
        peak = self.returns[0]
        for value in self.returns:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak
            max_drawdown = max(max_drawdown, drawdown)
        return max_drawdown

    # Add more performance metrics methods as needed