#!/usr/bin/env python3
"""Independent output checks for the twelve backtest invariants."""
from __future__ import annotations
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd
import yaml

ROOT=Path(__file__).resolve().parents[1]

def fail(message: str) -> int:
    print(f"ERROR: {message}",file=sys.stderr); return 2

def main() -> int:
    try:
        cfg=yaml.safe_load((ROOT/"config/base.yml").read_text(encoding="utf-8"))
        monthly=pd.read_csv(ROOT/"outputs/monthly_returns.csv",parse_dates=["date"]).set_index("date")
        nav=pd.read_csv(ROOT/"outputs/nav_curve.csv",parse_dates=["date"]).set_index("date")
        weights=pd.read_csv(ROOT/"outputs/allocation_weights.csv",parse_dates=["date"]).set_index("date")
        assets=pd.read_csv(ROOT/"outputs/asset_returns.csv",parse_dates=["date"]).set_index("date")
        macro=pd.read_csv(ROOT/"outputs/macro_scores.csv",parse_dates=["signal_date","observation_date","available_date"])
        reb=pd.read_csv(ROOT/"outputs/rebalance_records.csv",parse_dates=["signal_date","execution_date","return_period_end"])
        metrics=pd.read_csv(ROOT/"outputs/performance_metrics.csv").iloc[0]
        manifest=json.loads((ROOT/"outputs/input_manifest.json").read_text(encoding="utf-8"))
    except Exception as exc: return fail(f"cannot load outputs ({type(exc).__name__})")
    frames=[monthly,nav,weights,assets,macro,reb]
    if any(frame.isna().any().any() for frame in frames): return fail("an output contains null values")
    for frame in frames:
        numeric=frame.select_dtypes(include=[np.number])
        if not np.isfinite(numeric.to_numpy()).all(): return fail("an output contains non-finite values")
    if not (reb.signal_date < reb.execution_date).all(): return fail("signal is not earlier than execution")
    if not (reb.execution_date <= reb.return_period_end).all(): return fail("execution follows return-period end")
    if not (macro.observation_date <= macro.available_date).all() or not (macro.available_date <= macro.signal_date).all(): return fail("macro data used before available")
    if not np.allclose(weights.drop(columns="CASH").abs().sum(axis=1)+weights.CASH,1,atol=1e-10): return fail("weights violate gross-exposure constraint")
    expected=set(cfg["assets"])|{"CASH"}
    if set(weights)!=expected or set(assets)!=expected: return fail("asset mapping is incomplete")
    active=weights.abs()>1e-12
    if (active & assets.isna()).any().any(): return fail("held asset return is missing")
    expected_cost=monthly.turnover*float(cfg["project"]["transaction_cost_bps"])/10000
    if not np.allclose(monthly.transaction_cost,expected_cost,atol=1e-12): return fail("transaction costs do not equal turnover times cost rate")
    recalc_nav=(1+monthly.strategy_return).cumprod()
    if not np.allclose(nav.strategy_nav,recalc_nav,atol=1e-12): return fail("strategy NAV cannot be independently compounded")
    recalc_dd=recalc_nav/recalc_nav.cummax()-1
    if not np.isclose(float(metrics.max_drawdown),float(recalc_dd.min()),atol=1e-12): return fail("max drawdown cannot be independently reproduced")
    if not monthly.index.equals(nav.index) or not monthly.index.equals(weights.index) or not monthly.index.equals(assets.index): return fail("strategy and benchmark dates are not aligned")
    if monthly.index.max()>pd.Timestamp(cfg["data"]["as_of_date"]): return fail("latest result uses future return")
    if manifest.get("raw_redistribution") is not False or not manifest.get("inputs"): return fail("input manifest is incomplete")
    print("Backtest validation passed: 12 invariants checked, including timing, costs, compounding and finite outputs.")
    return 0
if __name__=="__main__": raise SystemExit(main())
