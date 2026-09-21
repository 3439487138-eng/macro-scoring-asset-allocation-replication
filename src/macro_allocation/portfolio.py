"""Factor aggregation and asset-position construction."""

from __future__ import annotations

from typing import Any

import pandas as pd

from .errors import DataValidationError


def build_asset_positions(
    signals: pd.DataFrame, factor_weights: dict[str, dict[str, Any]]
) -> pd.DataFrame:
    positions: dict[str, pd.Series] = {}
    for asset, raw_weights in factor_weights.items():
        weights = pd.Series(raw_weights, dtype=float)
        active = weights[weights.ne(0)]
        missing = sorted(set(active.index) - set(signals.columns))
        if missing:
            raise DataValidationError(f"{asset} is missing factor signals: {', '.join(missing)}")
        denominator = float(active.abs().sum())
        if denominator == 0:
            raise DataValidationError(f"{asset} has no active factor weights")
        aligned = signals[active.index]
        if aligned.isna().any().any():
            first = aligned.isna().stack()[lambda x: x].index[0]
            raise DataValidationError(
                f"missing factor cannot be treated as zero: date={first[0].date()}, factor={first[1]}"
            )
        positions[asset] = aligned.mul(active, axis=1).sum(axis=1) / denominator
    return pd.DataFrame(positions).dropna().sort_index()

