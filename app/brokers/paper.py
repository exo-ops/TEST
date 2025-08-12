from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from .base import Broker, Position


class PaperBroker(Broker):
    def __init__(self, state_path: Path) -> None:
        self.state_path = state_path
        self._state = {
            "cash": 0.0,
            "positions": {},  # symbol -> {quantity, average_price}
            "next_order_id": 1,
        }
        self._load()

    def _load(self) -> None:
        if self.state_path.exists():
            with open(self.state_path, "r", encoding="utf-8") as f:
                self._state = json.load(f)
        else:
            # ensure directory exists
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            self._save()

    def _save(self) -> None:
        with open(self.state_path, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2)

    def seed_cash(self, amount: float) -> None:
        if self._state["cash"] == 0.0 and self.total_equity() == 0.0:
            self._state["cash"] = float(amount)
            self._save()

    def total_equity(self, price_by_symbol: Dict[str, float] | None = None) -> float:
        equity = self._state.get("cash", 0.0)
        positions = self._state.get("positions", {})
        if price_by_symbol:
            for symbol, pos in positions.items():
                price = price_by_symbol.get(symbol)
                if price is not None:
                    equity += pos["quantity"] * price
        return float(equity)

    def get_cash(self) -> float:
        return float(self._state.get("cash", 0.0))

    def get_positions(self) -> Dict[str, Position]:
        result: Dict[str, Position] = {}
        for symbol, pos in self._state.get("positions", {}).items():
            result[symbol] = Position(
                symbol=symbol,
                quantity=int(pos["quantity"]),
                average_price=float(pos["average_price"]),
            )
        return result

    def place_order(self, symbol: str, quantity: int, side: str, price_hint: float | None = None) -> str:
        assert side in {"buy", "sell"}
        if quantity == 0:
            return "ORD-0"
        price = float(price_hint or 0.0)
        if price <= 0.0:
            raise ValueError("PaperBroker requires price_hint > 0 for execution")

        cash: float = float(self._state.get("cash", 0.0))
        positions = self._state.get("positions", {})
        pos = positions.get(symbol, {"quantity": 0, "average_price": 0.0})

        if side == "buy":
            cost = quantity * price
            if cost > cash + 1e-6:
                raise ValueError("Insufficient cash in PaperBroker")
            new_qty = pos["quantity"] + quantity
            new_avg = (
                0.0
                if new_qty == 0
                else (pos["quantity"] * pos["average_price"] + cost) / new_qty
            )
            pos.update({"quantity": new_qty, "average_price": new_avg})
            cash -= cost
        else:  # sell
            if quantity > pos["quantity"]:
                raise ValueError("Cannot sell more than current position in PaperBroker")
            revenue = quantity * price
            new_qty = pos["quantity"] - quantity
            if new_qty == 0:
                pos.update({"quantity": 0, "average_price": 0.0})
            else:
                pos.update({"quantity": new_qty})
            cash += revenue

        positions[symbol] = pos
        self._state["positions"] = positions
        self._state["cash"] = cash
        order_id = f"ORD-{self._state['next_order_id']}"
        self._state["next_order_id"] += 1
        self._save()
        return order_id