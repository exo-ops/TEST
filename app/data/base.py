from __future__ import annotations

from typing import Dict, Protocol, Sequence

import pandas as pd


class MarketDataProvider(Protocol):
    def get_history(self, symbols: Sequence[str], period: str = "1y", interval: str = "1d") -> Dict[str, pd.DataFrame]:
        ...

    def get_last_prices(self, symbols: Sequence[str]) -> Dict[str, float]:
        ...