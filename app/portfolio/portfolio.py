from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.brokers.base import Position


@dataclass
class OrderRequest:
    symbol: str
    side: str  # "buy" or "sell"
    quantity: int


def compute_rebalance_orders(
    target_weights: Dict[str, float],
    current_positions: Dict[str, Position],
    cash: float,
    last_prices: Dict[str, float],
    min_cash_reserve: float = 0.01,  # keep 1% cash buffer
) -> List[OrderRequest]:
    # compute total equity
    equity = cash
    for symbol, pos in current_positions.items():
        price = last_prices.get(symbol)
        if price is not None:
            equity += pos.quantity * price

    if equity <= 0:
        return []

    target_cash = equity * min_cash_reserve
    investable_equity = max(0.0, equity - target_cash)

    # calculate target dollar per symbol
    target_dollar: Dict[str, float] = {}
    for symbol, weight in target_weights.items():
        target_dollar[symbol] = investable_equity * max(0.0, min(1.0, weight))

    orders: List[OrderRequest] = []
    for symbol, td in target_dollar.items():
        price = last_prices.get(symbol)
        if price is None or price <= 0:
            continue
        current_quantity = current_positions.get(symbol, Position(symbol, 0, 0.0)).quantity
        current_dollar = current_quantity * price
        delta_dollar = td - current_dollar
        if abs(delta_dollar) < price:  # less than 1 share worth
            continue
        qty = int(delta_dollar // price)
        if qty > 0:
            orders.append(OrderRequest(symbol=symbol, side="buy", quantity=qty))
        elif qty < 0:
            orders.append(OrderRequest(symbol=symbol, side="sell", quantity=abs(qty)))

    # prioritize sells to free cash, then buys
    orders.sort(key=lambda o: 0 if o.side == "sell" else 1)
    return orders