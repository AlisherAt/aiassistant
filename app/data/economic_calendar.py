from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EconomicEvent:
    name: str
    impact: str
    when: str
    source: str = "manual"

    def as_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "impact": self.impact,
            "when": self.when,
            "source": self.source,
            "is_high_impact": self.impact.lower() in {"high", "important"},
        }


def get_next_events(limit: int = 5) -> list[dict[str, Any]]:
    events = [
        EconomicEvent("NFP", "high", "today").as_dict(),
        EconomicEvent("CPI", "high", "tomorrow").as_dict(),
        EconomicEvent("FOMC", "high", "this week").as_dict(),
        EconomicEvent("Retail sales", "medium", "this week").as_dict(),
    ]
    return events[:limit]
