"""One-period-lag backtest with strict missing-return handling."""

from __future__ import annotations

import pandas as pd

from .errors import DataValidationError
from .validation import ensure_no_missing_weighted_returns


def apply_one_period_lag(
    positions: pd.DataFrame, asset_returns: pd.DataFrame, lag: int = 1
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if lag != 1:
        raise DataValidationError("the preserved strategy requires exactly one portfolio lag")
    common = positions.index.intersection(asset_returns.index).sort_values()
    if len(common) < 2:
        raise DataValidationError("insufficient overlapping position/return dates")
    executed = positions.reindex(common).shift(1)
    returns = asset_returns.reindex(common)
    executed = executed.iloc[1:]
    returns = returns.iloc[1:]
    if executed.isna().any().any():
        raise DataValidationError("executed positions contain missing values after the initial lag")
    if returns.isna().any().any():
        first = returns.isna().stack()[lambda x: x].index[0]
        raise DataValidationError(
            f"missing asset return cannot be treated as zero: date={first[0].date()}, asset={first[1]}"
        )
    return executed, executed * returns


def portfolio_returns(
    asset_strategy_returns: pd.DataFrame, portfolio_weights: dict[str, float]
) -> pd.Series:
    weights = pd.Series(portfolio_weights, dtype=float)
    ensure_no_missing_weighted_returns(asset_strategy_returns, weights)
    if abs(float(weights.sum()) - 1.0) > 1e-12:
        raise DataValidationError("portfolio weights must sum to one")
    result = asset_strategy_returns.mul(weights, axis=1).sum(
        axis=1, min_count=len(weights)
    )
    if result.isna().any():
        raise DataValidationError("portfolio return contains unavailable values")
    return result.rename("strategy_return")

