from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol


@dataclass
class Position:
    symbol: str
    quantity: int
    average_price: float


class Broker(Protocol):
    def get_cash(self) -> float:
        ...

    def get_positions(self) -> Dict[str, Position]:
        ...

    def place_order(self, symbol: str, quantity: int, side: str, price_hint: float | None = None) -> str:
        """Place a market order. Returns broker order id or synthetic id.
        side: "buy" or "sell"
        price_hint: optional price for simulators
        """
        ...