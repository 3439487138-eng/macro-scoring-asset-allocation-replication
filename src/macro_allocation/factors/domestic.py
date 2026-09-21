"""Domestic China factor formulas preserved from the research notebooks."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..data import monthly_macro_panel
from ..errors import DataValidationError
from ..transforms import expanding_pca_last, require_complete


def _direction(values: pd.Series) -> pd.Series:
    return pd.Series(np.where(values.diff() >= 0, 1, -1), index=values.index, dtype=int)


def classify_expectation(level: float, delta: float, neutral_range: float = 5) -> str:
    if abs(level) < neutral_range:
        return "neutral"
    if level >= neutral_range and delta >= 0:
        return "expansion"
    if level >= neutral_range and delta < 0:
        return "normalization"
    if level <= -neutral_range and delta < 0:
        return "contraction"
    if level <= -neutral_range and delta >= 0:
        return "recovery"
    return "NA"


def domestic_expectation_signal(panel: pd.DataFrame, halflife: int, neutral_range: float) -> pd.Series:
    column = "china_expectation_of_trade"
    require_complete(panel[column], "domestic expectation")
    smoothed = panel[column].ewm(halflife=halflife).mean()
    level = smoothed - 100
    delta = smoothed.diff()
    regime = [classify_expectation(a, b, neutral_range) for a, b in zip(level, delta)]
    mapping = {
        "expansion": 0.5,
        "normalization": -1.0,
        "neutral": 0.0,
        "contraction": -0.5,
        "recovery": 1.0,
    }
    return pd.Series(regime, index=panel.index).map(mapping).rename("dom_expectation_signal")


def domestic_fx_signal(panel: pd.DataFrame, momentum_months: int, internal_lag_months: int) -> pd.Series:
    column = "china_CN"
    require_complete(panel[column], "domestic FX")
    momentum = panel[column].pct_change(momentum_months, fill_method=None)
    return np.sign(momentum.shift(internal_lag_months)).rename("dom_fx_signal")


def build_domestic_signals(
    raw: pd.DataFrame,
    factor_config: dict[str, Any],
    start: str,
    end: str,
    initial_window: int,
) -> pd.DataFrame:
    econ_cfg = factor_config["domestic_economy"]
    econ = monthly_macro_panel(raw, econ_cfg["indicators"], start, end, "domestic_macro")
    for column in econ_cfg["yoy_indicators"]:
        econ[column] = econ[column].pct_change(12, fill_method=None)
    econ = econ.dropna(how="all")
    econ_factor = expanding_pca_last(
        econ,
        initial_window,
        int(econ_cfg["smoothing_window"]),
    )

    currency_cfg = factor_config["domestic_currency"]
    currency = monthly_macro_panel(raw, currency_cfg["indicators"], start, end, "domestic_macro")
    require_complete(currency, "domestic currency")
    currency_components = -np.sign(
        currency.rolling(int(currency_cfg["smoothing_window"])).mean().diff(
            int(currency_cfg["change_periods"])
        )
    )
    currency_signal = (
        currency_components.mean(axis=1)
        .rolling(int(currency_cfg["signal_smoothing_window"]), min_periods=3)
        .mean()
        .rename("dom_curncy_signal")
    )

    credit_cfg = factor_config["domestic_credit"]
    credit = monthly_macro_panel(raw, credit_cfg["indicators"], start, end, "domestic_macro")
    column = credit_cfg["indicators"][0]
    credit_metric = (
        credit[column]
        .rolling(int(credit_cfg["rolling_sum_months"]))
        .sum()
        .pct_change(int(credit_cfg["yoy_periods"]), fill_method=None)
        .dropna()
        .to_frame(f"{column}_YoY")
    )
    credit_factor = expanding_pca_last(credit_metric, initial_window, 3)

    expectation_cfg = factor_config["domestic_expectation"]
    expectation = monthly_macro_panel(
        raw, expectation_cfg["indicators"], start, end, "domestic_macro"
    )
    expectation_signal = domestic_expectation_signal(
        expectation,
        int(expectation_cfg["ewm_halflife"]),
        float(expectation_cfg["neutral_range"]),
    )

    inflation_cfg = factor_config["domestic_inflation"]
    inflation = monthly_macro_panel(
        raw, inflation_cfg["indicators"], start, end, "domestic_macro"
    )
    inflation_factor = expanding_pca_last(inflation, initial_window, 3)
    delta = inflation_factor.diff()
    threshold = delta.rolling(int(inflation_cfg["threshold_window"])).std().shift(1)
    inflation_signal = pd.Series(0, index=delta.index, dtype=int)
    inflation_signal.loc[delta > threshold] = 1
    inflation_signal.loc[delta < -threshold] = -1
    inflation_signal.name = "dom_inflation_signal"

    fx_cfg = factor_config["domestic_fx"]
    fx = monthly_macro_panel(raw, fx_cfg["indicators"], start, end, "domestic_macro")
    fx_signal = domestic_fx_signal(
        fx, int(fx_cfg["momentum_months"]), int(fx_cfg["internal_lag_months"])
    )

    return pd.concat(
        [
            _direction(econ_factor).rename("dom_econ_signal"),
            currency_signal,
            _direction(credit_factor).rename("dom_credit_signal"),
            expectation_signal,
            inflation_signal,
            fx_signal,
        ],
        axis=1,
    ).sort_index()

