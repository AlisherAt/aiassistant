"""Simple trade lifecycle tracking with exit reasons."""

from __future__ import annotations


class TradeLifecycle:
    def __init__(self, entry_price: float, stop_loss: float, take_profit: float, size: float = 1.0):
        self.entry_price = float(entry_price)
        self.stop_loss = float(stop_loss)
        self.take_profit = float(take_profit)
        self.size = float(size)
        self.open = True
        self.closed_at = None
        self.exit_reason = None
        self.pnl = 0.0

    def exit_trade(self, reason: str, price: float):
        if not self.open:
            return {"status": "already_closed", "exit_reason": self.exit_reason, "pnl": self.pnl}

        self.open = False
        self.closed_at = price
        self.exit_reason = reason
        self.pnl = self._compute_pnl(price)
        return {
            "status": "closed",
            "exit_reason": reason,
            "close_price": price,
            "pnl": self.pnl,
        }

    def _compute_pnl(self, price: float) -> float:
        if self.entry_price <= 0:
            return 0.0
        return (price - self.entry_price) * self.size
