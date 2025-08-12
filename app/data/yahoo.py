from __future__ import annotations

from typing import Dict, Sequence

import pandas as pd
import yfinance as yf

from .base import MarketDataProvider


class YahooMarketDataProvider(MarketDataProvider):
    def get_history(self, symbols: Sequence[str], period: str = "1y", interval: str = "1d") -> Dict[str, pd.DataFrame]:
        data = yf.download(list(symbols), period=period, interval=interval, group_by="ticker", auto_adjust=False, progress=False)
        result: Dict[str, pd.DataFrame] = {}
        if isinstance(data.columns, pd.MultiIndex):
            for symbol in symbols:
                df = data[symbol].copy()
                # Normalize column names
                df.columns = [c.lower() for c in df.columns]
                result[symbol] = df
        else:
            df = data.copy()
            df.columns = [c.lower() for c in df.columns]
            # When single symbol requested, yfinance doesn't nest by ticker
            symbol = list(symbols)[0]
            result[symbol] = df
        return result

    def get_last_prices(self, symbols: Sequence[str]) -> Dict[str, float]:
        prices: Dict[str, float] = {}
        tickers = yf.Tickers(" ".join(symbols))
        for symbol in symbols:
            info = getattr(tickers.tickers.get(symbol), "fast_info", None)
            if info is not None:
                last_price = float(getattr(info, "last_price", 0.0))
                if last_price:
                    prices[symbol] = last_price
        # Fallback: use recent close from history if needed
        missing = [s for s in symbols if s not in prices]
        if missing:
            hist = self.get_history(missing, period="5d", interval="1d")
            for s, df in hist.items():
                if not df.empty and "close" in df.columns:
                    prices[s] = float(df["close"].iloc[-1])
        return prices