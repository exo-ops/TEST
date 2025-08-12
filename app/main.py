from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import typer

from app.config import get_settings
from app.utils.logging import configure_logging, get_logger
from app.brokers.paper import PaperBroker
from app.brokers.alpaca import AlpacaBroker
from app.data.yahoo import YahooMarketDataProvider
from app.portfolio.portfolio import compute_rebalance_orders
from app.strategy.sma_cross import SmaAboveStrategy


app = typer.Typer(add_completion=False)
logger = get_logger(__name__)


def _init_broker(name: str, state_dir: Path) -> object:
    settings = get_settings()
    if name == "paper":
        return PaperBroker(state_path=state_dir / "paper_state.json")
    if name == "alpaca":
        if not settings.alpaca_key_id or not settings.alpaca_secret_key:
            raise typer.BadParameter("Alpaca credentials are not set in environment/.env")
        return AlpacaBroker(
            base_url=settings.alpaca_base_url,
            key_id=settings.alpaca_key_id,
            secret_key=settings.alpaca_secret_key,
        )
    raise typer.BadParameter(f"Unknown broker: {name}")


@app.command()
def run(
    symbols: List[str] = typer.Option(..., "--symbols", help="Список тикеров (через пробел)", show_default=False),
    broker: str = typer.Option("paper", "--broker", help="paper или alpaca"),
    budget: float = typer.Option(0.0, "--budget", help="Начальный бюджет для paper-симуляции (USD)"),
    warmup: int = typer.Option(200, "--warmup", help="Количество баров истории для стратегии"),
    short_sma: int = typer.Option(50, "--short-sma", help="Окно короткой SMA"),
    long_sma: int = typer.Option(200, "--long-sma", help="Окно длинной SMA"),
) -> None:
    """Выполнить один цикл ребалансировки портфеля по стратегии SMA."""
    configure_logging()
    settings = get_settings()

    if not symbols:
        raise typer.BadParameter("Не задан список тикеров")

    logger.info("Инициализация брокера: %s", broker)
    brk = _init_broker(broker, settings.state_dir)

    if isinstance(brk, PaperBroker) and budget > 0:
        brk.seed_cash(budget)

    logger.info("Загрузка исторических данных из Yahoo Finance")
    data_provider = YahooMarketDataProvider()
    history = data_provider.get_history(symbols, period=f"{max(warmup, long_sma) + 10}d", interval="1d")

    # Обрезаем до нужной длины warmup
    for s, df in history.items():
        if len(df) > warmup:
            history[s] = df.tail(warmup)

    logger.info("Расчёт целевых весов стратегии SMA")
    strategy = SmaAboveStrategy(short_window=short_sma, long_window=long_sma)
    target_weights = strategy.compute_target_weights(history)

    logger.info("Получение текущих позиций и кэша")
    positions = brk.get_positions()  # type: ignore[attr-defined]
    cash = brk.get_cash()  # type: ignore[attr-defined]

    logger.info("Получение последних цен")
    last_prices = data_provider.get_last_prices(symbols)

    orders = compute_rebalance_orders(target_weights, positions, cash, last_prices)

    if not orders:
        logger.info("Ордеров для исполнения нет. Портфель уже соответствует целевым весам или нет сигналов.")
        return

    logger.info("Отправка ордеров (%d шт.)", len(orders))
    for order in orders:
        price_hint = last_prices.get(order.symbol)
        order_id = brk.place_order(order.symbol, order.quantity, order.side, price_hint=price_hint)  # type: ignore[attr-defined]
        logger.info("%s %s x %d @ ~%.2f -> %s", order.side.upper(), order.symbol, order.quantity, price_hint or 0.0, order_id)

    # Итоговое состояние
    positions_after = brk.get_positions()  # type: ignore[attr-defined]
    last_prices_after = data_provider.get_last_prices(list(positions_after.keys()))
    equity = cash
    for sym, pos in positions_after.items():
        p = last_prices_after.get(sym)
        if p is not None:
            equity += pos.quantity * p
    logger.info("Завершено. Текущая оценка портфеля: %.2f USD", equity)


if __name__ == "__main__":
    app()