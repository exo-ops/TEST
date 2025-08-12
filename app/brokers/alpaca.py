from __future__ import annotations

import httpx
from typing import Dict

from .base import Broker, Position


class AlpacaBroker(Broker):
    def __init__(self, base_url: str, key_id: str, secret_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = httpx.Client(
            base_url=self.base_url,
            headers={
                "APCA-API-KEY-ID": key_id,
                "APCA-API-SECRET-KEY": secret_key,
                "Content-Type": "application/json",
            },
            timeout=20.0,
        )

    def get_cash(self) -> float:
        resp = self.session.get("/v2/account")
        resp.raise_for_status()
        data = resp.json()
        return float(data.get("cash", 0.0))

    def get_positions(self) -> Dict[str, Position]:
        resp = self.session.get("/v2/positions")
        resp.raise_for_status()
        positions = {}
        for p in resp.json():
            symbol = p["symbol"]
            qty = int(float(p["qty"]))
            avg = float(p.get("avg_entry_price", 0.0))
            positions[symbol] = Position(symbol=symbol, quantity=qty, average_price=avg)
        return positions

    def place_order(self, symbol: str, quantity: int, side: str, price_hint: float | None = None) -> str:
        assert side in {"buy", "sell"}
        if quantity == 0:
            return "ORD-0"
        payload = {
            "symbol": symbol,
            "qty": quantity,
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        resp = self.session.post("/v2/orders", json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data.get("id", "")