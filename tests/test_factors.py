from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from macro_allocation.errors import DataValidationError, ReproductionIncomplete
from macro_allocation.factors.domestic import (
    classify_expectation,
    domestic_fx_signal,
)
from macro_allocation.transforms import _check_loading_orientation
from macro_allocation.validation import check_release_dates_not_after_signal
from macro_allocation.practical_factors import causal_winsorized_zscore


def test_domestic_expectation_mapping_formula() -> None:
    assert classify_expectation(6, 1) == "expansion"
    assert classify_expectation(6, -1) == "normalization"
    assert classify_expectation(-6, -1) == "contraction"
    assert classify_expectation(-6, 1) == "recovery"
    assert classify_expectation(2, 99) == "neutral"


def test_domestic_fx_preserves_internal_lag() -> None:
    dates = pd.date_range("2020-01-31", periods=5, freq="ME")
    panel = pd.DataFrame({"china_CN": [100, 101, 102, 104, 103]}, index=dates)
    signal = domestic_fx_signal(panel, momentum_months=3, internal_lag_months=1)
    assert pd.isna(signal.iloc[3])
    assert signal.iloc[4] == 1


def test_pca_sign_flip_is_detected_not_corrected() -> None:
    with pytest.raises(ReproductionIncomplete, match="sign flipped"):
        _check_loading_orientation(np.array([1.0, 0.0]), np.array([-1.0, 0.0]))


def test_release_date_after_signal_is_lookahead() -> None:
    with pytest.raises(DataValidationError, match="look-ahead"):
        check_release_dates_not_after_signal(
            pd.Series(["2020-02-01"]), pd.Series(["2020-01-31"])
        )


def test_future_change_does_not_alter_earlier_causal_score() -> None:
    dates = pd.date_range("2010-01-31", periods=40, freq="ME")
    original = pd.Series(np.linspace(1, 2, 40), index=dates)
    changed = original.copy(); changed.iloc[-1] = 999
    left = causal_winsorized_zscore(original, 24, 12, .05, .95)
    right = causal_winsorized_zscore(changed, 24, 12, .05, .95)
    pd.testing.assert_series_equal(left.iloc[:-1], right.iloc[:-1])
