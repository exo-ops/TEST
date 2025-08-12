from __future__ import annotations

from typing import Dict

import pandas as pd

from .base import Strategy


class SmaAboveStrategy(Strategy):
    def __init__(self, short_window: int = 50, long_window: int = 200) -> None:
        self.short_window = short_window
        self.long_window = long_window

    def compute_target_weights(self, price_history_by_symbol: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        bullish: Dict[str, bool] = {}
        for symbol, df in price_history_by_symbol.items():
            if df.empty or "close" not in df.columns:
                bullish[symbol] = False
                continue
            close = df["close"].dropna()
            if len(close) < max(self.short_window, self.long_window):
                bullish[symbol] = False
                continue
            sma_short = close.rolling(window=self.short_window).mean()
            sma_long = close.rolling(window=self.long_window).mean()
            bullish[symbol] = bool(close.iloc[-1] > sma_short.iloc[-1] > sma_long.iloc[-1])
        winners = [s for s, ok in bullish.items() if ok]
        if not winners:
            return {s: 0.0 for s in price_history_by_symbol.keys()}
        weight = 1.0 / len(winners)
        return {s: (weight if s in winners else 0.0) for s in price_history_by_symbol.keys()}