from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from macro_allocation.backtest import apply_one_period_lag, portfolio_returns
from macro_allocation.errors import DataValidationError


FIXTURES = Path(__file__).parent / "fixtures"


def _load(name: str) -> pd.DataFrame:
    return pd.read_csv(FIXTURES / name, parse_dates=["date"]).set_index("date")


def test_signal_is_applied_exactly_one_period_later() -> None:
    executed, strategy = apply_one_period_lag(
        _load("lag_positions.csv"), _load("lag_returns.csv"), lag=1
    )
    assert executed["A"].tolist() == [1.0, 2.0]
    assert strategy["A"].tolist() == pytest.approx([0.02, 0.06])


def test_missing_return_is_not_silently_zeroed() -> None:
    returns = _load("lag_returns.csv")
    returns.loc[pd.Timestamp("2020-02-29"), "A"] = None
    with pytest.raises(DataValidationError, match="cannot be treated as zero"):
        apply_one_period_lag(_load("lag_positions.csv"), returns, lag=1)


def test_portfolio_key_mismatch_is_fatal() -> None:
    returns = _load("lag_returns.csv").iloc[1:]
    with pytest.raises(DataValidationError, match="columns differ"):
        portfolio_returns(returns, {"CREDIT": 1.0})


def test_portfolio_requires_all_weighted_returns() -> None:
    returns = _load("lag_returns.csv").iloc[1:]
    returns.iloc[0, 0] = None
    with pytest.raises(DataValidationError, match="cannot be treated as zero"):
        portfolio_returns(returns, {"A": 1.0})

