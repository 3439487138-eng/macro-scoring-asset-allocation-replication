"""Independently reproducible performance metrics."""
from __future__ import annotations
import numpy as np
import pandas as pd
from .errors import DataValidationError

def build_nav(monthly: pd.DataFrame) -> pd.DataFrame:
    strategy = (1 + monthly["strategy_return"]).cumprod()
    benchmark = (1 + monthly["benchmark_return"]).cumprod()
    return pd.DataFrame({"strategy_nav": strategy, "benchmark_nav": benchmark,
                         "strategy_drawdown": strategy / strategy.cummax() - 1,
                         "benchmark_drawdown": benchmark / benchmark.cummax() - 1})

def _annualized(nav_end: float, n: int) -> float:
    return float(nav_end ** (12.0 / n) - 1.0)

def compute_metrics(monthly: pd.DataFrame, data_cutoff: str, risk_free_rate: float = 0.0) -> dict[str, object]:
    required = {"strategy_return", "benchmark_return", "turnover", "transaction_cost"}
    if not required.issubset(monthly) or monthly.empty or monthly.isna().any().any() or not np.isfinite(monthly.to_numpy()).all():
        raise DataValidationError("metrics input must be non-empty, complete and finite")
    nav = build_nav(monthly); strategy = monthly["strategy_return"]
    annual_vol = float(strategy.std(ddof=1) * np.sqrt(12)); annual = _annualized(float(nav.strategy_nav.iloc[-1]), len(monthly))
    benchmark_annual = _annualized(float(nav.benchmark_nav.iloc[-1]), len(monthly))
    return {"data_cutoff_date": str(data_cutoff), "backtest_start": monthly.index.min().date().isoformat(),
            "backtest_end": monthly.index.max().date().isoformat(), "observations": int(len(monthly)),
            "cumulative_return": float(nav.strategy_nav.iloc[-1] - 1), "annualized_return": annual,
            "annualized_volatility": annual_vol, "sharpe_ratio": float((annual-risk_free_rate)/annual_vol) if annual_vol else 0.0,
            "max_drawdown": float(nav.strategy_drawdown.min()), "monthly_win_rate": float((strategy > 0).mean()),
            "rebalance_count": int(len(monthly)), "annualized_turnover": float(monthly.turnover.mean()*12),
            "total_transaction_cost": float(monthly.transaction_cost.sum()),
            "benchmark_cumulative_return": float(nav.benchmark_nav.iloc[-1]-1),
            "benchmark_annualized_return": benchmark_annual,
            "excess_cumulative_return": float(nav.strategy_nav.iloc[-1]-nav.benchmark_nav.iloc[-1]),
            "excess_annualized_return": float(annual-benchmark_annual)}
