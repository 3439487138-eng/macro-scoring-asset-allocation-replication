"""Global factor formulas preserved from the multi-asset notebook."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from ..data import monthly_macro_panel
from ..transforms import (
    ewm_zscore,
    expanding_hp_endpoint,
    expanding_pca_last,
    require_complete,
    threshold_signal,
)


def _persistent_rate_signal(changes: pd.Series, threshold: float) -> pd.Series:
    """Explicit state machine equivalent to the notebook's derived-signal ffill."""
    state = 0
    output: list[int] = []
    for value in changes:
        if pd.notna(value) and abs(float(value)) >= threshold:
            state = int(-np.sign(value))
        output.append(state)
    return pd.Series(output, index=changes.index, dtype=int)


def build_global_signals(
    raw: pd.DataFrame,
    factor_config: dict[str, Any],
    start: str,
    end: str,
    initial_window: int,
) -> pd.DataFrame:
    econ_cfg = factor_config["global_economy"]
    econ = monthly_macro_panel(raw, econ_cfg["indicators"], start, end, "global_macro")
    econ[["usa_pmi", "china_pmi_new_export_orders"]] -= 50
    econ["korea_exports"] = (
        econ["korea_exports"].pct_change(12, fill_method=None).rolling(6).mean()
    )
    econ["copper/gold"] = np.log(econ["copper_lme"] / econ["gold"]).rolling(6).mean()
    econ = econ[["usa_pmi", "china_pmi_new_export_orders", "korea_exports", "copper/gold"]]
    econ_factor = expanding_pca_last(
        econ.dropna(), initial_window, int(econ_cfg["smoothing_window"])
    )
    econ_signal = np.sign(econ_factor.diff()).rename("global_econ_signal")

    currency_cfg = factor_config["global_currency"]
    currency = monthly_macro_panel(
        raw, currency_cfg["indicators"], start, end, "global_macro"
    ).dropna()
    require_complete(currency, "global currency")
    smoothed_yield = currency["treasury_yld_1y"].rolling(
        int(currency_cfg["yield_smoothing_window"])
    ).mean()
    yield_signal = _persistent_rate_signal(
        smoothed_yield.diff(), float(currency_cfg["rate_threshold"])
    )
    holdings_signal = (
        2
        * (
            (currency["fed_securities_bs"] / 1000).diff()
            > float(currency_cfg["holdings_change_threshold"])
        ).astype(int)
        - 1
    )
    global_currency_signal = pd.Series(
        np.where(
            smoothed_yield < float(currency_cfg["low_yield_threshold"]),
            holdings_signal,
            yield_signal,
        ),
        index=currency.index,
        name="global_curncy_signal",
    )

    inflation_cfg = factor_config["global_inflation"]
    inflation = monthly_macro_panel(
        raw, inflation_cfg["indicators"], start, end, "global_macro"
    )[inflation_cfg["indicators"][0]]
    inflation_trend = expanding_hp_endpoint(inflation, float(inflation_cfg["hp_lambda"]))
    inflation_signal = threshold_signal(
        ewm_zscore(inflation_trend, 12), float(inflation_cfg["z_threshold"])
    ).rename("global_inflation_signal")

    dollar_cfg = factor_config["dollar_cycle"]
    dollar = monthly_macro_panel(raw, dollar_cfg["indicators"], start, end, "global_macro")[
        dollar_cfg["indicators"][0]
    ]
    dollar_trend = expanding_hp_endpoint(dollar, float(dollar_cfg["hp_lambda"]))
    dollar_signal = threshold_signal(
        ewm_zscore(dollar_trend, 12), float(dollar_cfg["z_threshold"])
    ).rename("dollar_cycle_signal")

    risk_cfg = factor_config["global_financial_risk"]
    risk = monthly_macro_panel(raw, risk_cfg["indicators"], start, end, "global_macro")[
        risk_cfg["indicators"][0]
    ]
    require_complete(risk, "global financial risk")
    risk_signal = threshold_signal(
        ewm_zscore(risk, int(risk_cfg["ewm_halflife"])),
        float(risk_cfg["z_threshold"]),
    ).rename("fin_risk_signal")

    return pd.concat(
        [econ_signal, global_currency_signal, inflation_signal, dollar_signal, risk_signal],
        axis=1,
    ).sort_index()

