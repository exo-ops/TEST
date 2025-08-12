from __future__ import annotations

from typing import Dict, Protocol

import pandas as pd


class Strategy(Protocol):
    def compute_target_weights(self, price_history_by_symbol: Dict[str, pd.DataFrame]) -> Dict[str, float]:
        """Return target weights (0..1) for each symbol. Sum may be <= 1 (cash remainder)."""
        ...