"""Portfolio metrics computed only from the current run."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from .errors import DataValidationError


def compute_metrics(returns: pd.Series, periods_per_year: int = 12) -> dict[str, float | int | str]:
    if returns.empty or returns.isna().any():
        raise DataValidationError("metrics require non-empty finite returns")
    if not np.isfinite(returns.to_numpy()).all():
        raise DataValidationError("metrics require finite returns")
    nav = (1 + returns).cumprod()
    years = len(returns) / periods_per_year
    total = float(nav.iloc[-1] - 1)
    annualized = float(nav.iloc[-1] ** (1 / years) - 1) if years > 0 else math.nan
    volatility = float(returns.std() * np.sqrt(periods_per_year))
    sharpe = float(returns.mean() * periods_per_year / volatility) if volatility else math.nan
    drawdown = nav / nav.cummax() - 1
    maximum = float(drawdown.min())
    duration = int(_max_drawdown_duration(drawdown))
    return {
        "period_start": returns.index.min().date().isoformat(),
        "period_end": returns.index.max().date().isoformat(),
        "observations": int(len(returns)),
        "total_return": total,
        "annualized_return": annualized,
        "annualized_volatility": volatility,
        "sharpe_0rf": sharpe,
        "max_drawdown": maximum,
        "max_drawdown_duration_months": duration,
    }


def _max_drawdown_duration(drawdown: pd.Series) -> int:
    longest = current = 0
    for value in drawdown:
        if value < 0:
            current += 1
            longest = max(longest, current)
        else:
            current = 0
    return longest


def build_nav(returns: pd.Series) -> pd.DataFrame:
    nav = (1 + returns).cumprod()
    return pd.DataFrame(
        {
            "strategy_return": returns,
            "strategy_nav": nav,
            "drawdown": nav / nav.cummax() - 1,
        }
    )

