"""Strict one-period-lag backtest with explicit cash and transaction costs."""
from __future__ import annotations
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .errors import DataValidationError

@dataclass(frozen=True)
class BacktestResult:
    allocations: pd.DataFrame
    monthly: pd.DataFrame
    rebalance: pd.DataFrame

def run_backtest(positions: pd.DataFrame, asset_returns: pd.DataFrame,
                 cash_returns: pd.Series, base_weights: dict[str, float],
                 transaction_cost_bps: float, sample_start: str,
                 daily_prices: dict[str, pd.Series] | None = None,
                 asset_symbols: dict[str, str] | None = None) -> BacktestResult:
    keys = set(base_weights)
    if set(positions) != keys or set(asset_returns) != keys:
        raise DataValidationError("asset positions, returns and base-weight keys must match exactly")
    if positions.isna().any().any() or not np.isfinite(positions.to_numpy()).all():
        raise DataValidationError("positions must be complete and finite")
    if (positions.abs() > 1 + 1e-12).any().any():
        raise DataValidationError("asset position is outside [-1, 1]")
    common = positions.index.intersection(asset_returns.index).intersection(cash_returns.index).sort_values()
    if len(common) < 3:
        raise DataValidationError("insufficient overlapping monthly observations")
    target = positions.reindex(common).mul(pd.Series(base_weights), axis=1)
    executed = target.shift(1).iloc[1:]
    returns = asset_returns.reindex(common).iloc[1:]
    cash = cash_returns.reindex(common).iloc[1:]
    keep = executed.index >= pd.Timestamp(sample_start)
    executed, returns, cash = executed.loc[keep], returns.loc[keep], cash.loc[keep]
    if returns.isna().any().any() or cash.isna().any():
        missing = returns.isna().stack()
        if missing.any():
            date, asset = missing[missing].index[0]
            raise DataValidationError(f"missing held return cannot be treated as zero: {date.date()} {asset}")
        raise DataValidationError("missing cash return cannot be treated as zero")
    if not np.isfinite(returns.to_numpy()).all() or not np.isfinite(cash.to_numpy()).all():
        raise DataValidationError("returns must be finite")
    allocations = executed.copy()
    allocations["CASH"] = 1.0 - executed.abs().sum(axis=1)
    if (allocations["CASH"] < -1e-12).any():
        raise DataValidationError("risky gross exposure exceeds one")
    allocations["CASH"] = allocations["CASH"].clip(lower=0)
    if not np.allclose(executed.abs().sum(axis=1) + allocations["CASH"], 1.0, atol=1e-12):
        raise DataValidationError("allocation gross exposure does not equal one")
    previous = allocations.shift(1)
    previous.iloc[0] = 0.0
    previous.iloc[0, previous.columns.get_loc("CASH")] = 1.0
    turnover = (allocations - previous).abs().sum(axis=1) / 2.0
    cost = turnover * float(transaction_cost_bps) / 10000.0
    gross = (executed * returns).sum(axis=1, min_count=len(keys)) + allocations["CASH"] * cash
    benchmark = returns.mul(pd.Series(base_weights), axis=1).sum(axis=1, min_count=len(keys))
    monthly = pd.DataFrame({"gross_return": gross, "transaction_cost": cost,
                            "strategy_return": gross - cost, "benchmark_return": benchmark,
                            "excess_return": gross - cost - benchmark, "turnover": turnover})
    if monthly.isna().any().any() or not np.isfinite(monthly.to_numpy()).all():
        raise DataValidationError("computed return table is incomplete or non-finite")
    signal_dates = pd.Series(common[:-1], index=common[1:]).reindex(monthly.index)
    execution_dates = []
    for date, signal_date in signal_dates.items():
        candidates = []
        if daily_prices and asset_symbols:
            for asset, symbol in asset_symbols.items():
                if abs(float(allocations.loc[date, asset])) > 1e-12:
                    later = daily_prices[symbol].index[daily_prices[symbol].index > signal_date]
                    if len(later): candidates.append(later[0])
        execution_dates.append(max(candidates) if candidates else signal_date + pd.offsets.BDay(1))
    rebalance = pd.DataFrame({"signal_date": signal_dates.to_numpy(),
                              "execution_date": execution_dates,
                              "return_period_end": monthly.index,
                              "turnover": turnover.to_numpy(),
                              "transaction_cost": cost.to_numpy()})
    if not (rebalance["signal_date"] < rebalance["execution_date"]).all():
        raise DataValidationError("signal date must precede execution date")
    if not (rebalance["execution_date"] <= rebalance["return_period_end"]).all():
        raise DataValidationError("execution date must not follow return period end")
    return BacktestResult(allocations, monthly, rebalance)
