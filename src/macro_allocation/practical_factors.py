"""Causal market-implied macro scores for the documented practical adaptation."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from .errors import DataValidationError
from .factors.autoregression import autoregressive_signal


def monthly_prices(daily: dict[str, pd.Series], as_of_date: str) -> pd.DataFrame:
    columns = {symbol: series.resample("ME").last() for symbol, series in daily.items()}
    frame = pd.DataFrame(columns).sort_index().loc[:as_of_date]
    if frame.index.duplicated().any():
        raise DataValidationError("monthly price index contains duplicate dates")
    return frame


def causal_winsorized_zscore(
    series: pd.Series,
    window: int,
    min_history: int,
    lower_quantile: float,
    upper_quantile: float,
) -> pd.Series:
    lower = series.rolling(window, min_periods=min_history).quantile(lower_quantile)
    upper = series.rolling(window, min_periods=min_history).quantile(upper_quantile)
    clipped = series.clip(lower=lower, upper=upper)
    mean = clipped.rolling(window, min_periods=min_history).mean()
    std = clipped.rolling(window, min_periods=min_history).std(ddof=0)
    return ((clipped - mean) / std.replace(0, np.nan)).rename(series.name)


def _momentum(series: pd.Series, months: int) -> pd.Series:
    if (series.dropna() <= 0).any():
        raise DataValidationError(f"non-positive price in proxy {series.name}")
    return np.log(series).diff(months)


def build_macro_scores(prices: pd.DataFrame, config: dict[str, Any]) -> pd.DataFrame:
    model = config["factor_model"]
    asset_symbol = {key: value["symbol"] for key, value in config["assets"].items()}
    proxy_symbol = {key: value["symbol"] for key, value in config["macro_proxies"].items()}
    cash_symbol = config["cash"]["symbol"]
    needed = set(asset_symbol.values()) | set(proxy_symbol.values()) | {cash_symbol}
    missing = sorted(needed - set(prices.columns))
    if missing:
        raise DataValidationError(f"missing market proxy columns: {', '.join(missing)}")

    raw = pd.DataFrame(index=prices.index)
    raw["dom_econ"] = _momentum(prices[asset_symbol["CH_EQUITY"]], int(model["domestic_economy_momentum_months"]))
    raw["dom_curncy"] = -_momentum(prices[proxy_symbol["CNY"]], int(model["domestic_currency_momentum_months"]))
    raw["dom_credit"] = _momentum(prices[asset_symbol["CREDIT"]] / prices[asset_symbol["CH_BOND"]], int(model["domestic_credit_momentum_months"]))
    raw["dom_expectation"] = _momentum(prices[asset_symbol["CH_EQUITY"]] / prices[asset_symbol["US_EQUITY"]], int(model["domestic_expectation_momentum_months"]))
    raw["dom_inflation"] = _momentum(prices[asset_symbol["OIL"]] / prices[asset_symbol["GOLD"]], int(model["domestic_inflation_momentum_months"]))
    raw["dom_fx"] = -_momentum(prices[proxy_symbol["CNY"]], int(model["domestic_currency_momentum_months"]))
    raw["global_econ_component_spy"] = _momentum(prices[asset_symbol["US_EQUITY"]], int(model["global_economy_momentum_months"]))
    raw["global_econ_component_copper_gold"] = _momentum(prices[proxy_symbol["COPPER"]] / prices[proxy_symbol["GOLD_FUTURE"]], int(model["global_economy_momentum_months"]))
    raw["global_curncy"] = _momentum(prices[proxy_symbol["LONG_TREASURY"]] / prices[cash_symbol], int(model["global_currency_momentum_months"]))
    raw["global_inflation"] = _momentum(prices[asset_symbol["OIL"]], int(model["global_inflation_momentum_months"]))
    raw["dollar_cycle"] = _momentum(prices[proxy_symbol["DOLLAR"]], int(model["dollar_cycle_momentum_months"]))
    raw["fin_risk"] = np.log(prices[proxy_symbol["VIX"]])

    params = (int(model["winsor_window_months"]), int(model["min_history_months"]), float(model["lower_quantile"]), float(model["upper_quantile"]))
    scores = pd.DataFrame(index=prices.index)
    names = ["dom_econ", "dom_curncy", "dom_credit", "dom_expectation", "dom_inflation", "dom_fx", "global_curncy", "global_inflation", "dollar_cycle", "fin_risk"]
    for name in names:
        scores[f"{name}_score"] = causal_winsorized_zscore(raw[name], *params)
    global_spy = causal_winsorized_zscore(raw["global_econ_component_spy"], *params)
    global_cg = causal_winsorized_zscore(raw["global_econ_component_copper_gold"], *params)
    scores["global_econ_score"] = (global_spy + global_cg) / 2.0

    signal_names = {
        "dom_econ": "dom_econ_signal", "dom_curncy": "dom_curncy_signal",
        "dom_credit": "dom_credit_signal", "dom_expectation": "dom_expectation_signal",
        "dom_inflation": "dom_inflation_signal", "dom_fx": "dom_fx_signal",
        "global_econ": "global_econ_signal", "global_curncy": "global_curncy_signal",
        "global_inflation": "global_inflation_signal", "dollar_cycle": "dollar_cycle_signal",
        "fin_risk": "fin_risk_signal",
    }
    for source, target in signal_names.items():
        scores[target] = np.sign(scores[f"{source}_score"])

    china_returns = prices[asset_symbol["CH_EQUITY"]].pct_change(fill_method=None)
    scores["ar_signal"] = autoregressive_signal(
        china_returns,
        lags=int(model["autoregression_lags"]),
        initial_window=int(model["autoregression_initial_window"]),
    ).reindex(scores.index)
    required = [column for column in scores if column.endswith("_score") or column.endswith("_signal")]
    complete = scores[required].dropna().copy()
    complete.insert(0, "available_date", complete.index)
    complete.insert(0, "observation_date", complete.index)
    return complete.sort_index()


def build_asset_returns(prices: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, pd.Series]:
    returns = pd.DataFrame(index=prices.index)
    for asset, spec in config["assets"].items():
        returns[asset] = prices[spec["symbol"]].pct_change(fill_method=None)
    cash = prices[config["cash"]["symbol"]].pct_change(fill_method=None).rename("CASH")
    return returns, cash
