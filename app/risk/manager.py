"""Risk manager and lot-sizing utilities for the gold trading system."""

from __future__ import annotations


class RiskManager:
    def __init__(self, account_balance: float = 10000.0, risk_per_trade: float = 0.005, max_daily_loss: float = 0.02, max_open_positions: int = 1):
        self.account_balance = float(account_balance)
        self.risk_per_trade = float(risk_per_trade)
        self.max_daily_loss = float(max_daily_loss)
        self.max_open_positions = int(max_open_positions)

    @property
    def risk_amount(self) -> float:
        return self.account_balance * self.risk_per_trade

    @property
    def daily_loss_limit(self) -> float:
        return self.account_balance * self.max_daily_loss


class PositionSizer:
    def __init__(self, risk: RiskManager, entry_price: float, stop_loss: float, lot_size: float = 0.01, contract_value: float = 100.0):
        self.risk = risk
        self.entry_price = float(entry_price)
        self.stop_loss = float(stop_loss)
        self.lot_size = float(lot_size)
        self.contract_value = float(contract_value)

    def position_size(self) -> float:
        risk_per_unit = abs(self.entry_price - self.stop_loss)
        if risk_per_unit <= 0:
            return self.lot_size
        base_size = (self.risk.risk_amount / (risk_per_unit * self.contract_value))
        return max(self.lot_size, min(base_size, 2.0))
