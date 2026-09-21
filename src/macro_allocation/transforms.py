"""Deterministic transformations extracted from the research notebooks."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from statsmodels.tsa.filters.hp_filter import hpfilter
from statsmodels.tsa.seasonal import seasonal_decompose

from .errors import DataValidationError, ReproductionIncomplete


def require_complete(frame: pd.DataFrame | pd.Series, label: str) -> None:
    if frame.empty:
        raise DataValidationError(f"{label} is empty")
    missing = int(frame.isna().sum().sum()) if isinstance(frame, pd.DataFrame) else int(frame.isna().sum())
    if missing:
        raise DataValidationError(f"{label} contains {missing} missing observations")


def seasonal_adjust(frame: pd.DataFrame, period: int = 12) -> pd.DataFrame:
    require_complete(frame, "seasonal adjustment input")
    adjusted = pd.DataFrame(index=frame.index)
    for column in frame.columns:
        decomposition = seasonal_decompose(
            frame[column], model="additive", period=period, extrapolate_trend="freq"
        )
        adjusted[column] = frame[column] - decomposition.seasonal
    return adjusted


def trailing_smooth(frame: pd.DataFrame, window: int) -> pd.DataFrame:
    """Notebook trailing rolling mean; no centered window and no edge filling."""
    result = frame.rolling(window=window).mean().dropna()
    require_complete(result, "trailing smoothing result")
    return result


def standardize(frame: pd.DataFrame) -> pd.DataFrame:
    require_complete(frame, "standardization input")
    values = StandardScaler().fit_transform(frame)
    return pd.DataFrame(values, index=frame.index, columns=frame.columns)


def _check_loading_orientation(previous: np.ndarray, current: np.ndarray) -> None:
    if float(np.dot(previous, current)) < 0:
        raise ReproductionIncomplete(
            "PCA component sign flipped across expanding windows; no automatic sign correction is allowed"
        )


def expanding_pca_last(
    frame: pd.DataFrame,
    initial_window: int,
    smoothing_window: int,
    seasonal: bool = True,
) -> pd.Series:
    """Reproduce expanding-window PCA and fail on arbitrary component sign flips."""
    if len(frame) < initial_window:
        raise DataValidationError("insufficient rows for expanding PCA")
    values: list[tuple[pd.Timestamp, float]] = []
    previous_loading: np.ndarray | None = None
    for end in range(initial_window, len(frame) + 1):
        window = frame.iloc[:end]
        require_complete(window, "expanding PCA raw window")
        transformed = seasonal_adjust(window) if seasonal else window.copy()
        transformed = trailing_smooth(transformed, smoothing_window)
        scaled = standardize(transformed)
        model = PCA(n_components=1)
        component = model.fit_transform(scaled)
        loading = model.components_[0]
        if previous_loading is not None:
            _check_loading_orientation(previous_loading, loading)
        previous_loading = loading.copy()
        values.append((scaled.index[-1], float(component[-1, 0])))
    return pd.Series(dict(values), name="factor").sort_index()


def ewm_zscore(series: pd.Series, halflife: int, min_periods: int = 12) -> pd.Series:
    mean = series.ewm(halflife=halflife, min_periods=min_periods).mean()
    std = series.ewm(halflife=halflife, min_periods=min_periods).std()
    return (series - mean) / std


def expanding_hp_endpoint(series: pd.Series, lamb: float, warmup: int = 12) -> pd.Series:
    series = series.loc[series.first_valid_index() :]
    require_complete(series, "HP filter source")
    month_ends = series.resample("ME").last().index
    points: list[tuple[pd.Timestamp, float]] = []
    for date in month_ends[warmup:]:
        history = series.loc[:date]
        _, trend = hpfilter(history, lamb=lamb)
        points.append((date, float(trend.iloc[-1])))
    return pd.Series(dict(points), name=series.name).sort_index()


def threshold_signal(values: pd.Series, threshold: float = 1.0) -> pd.Series:
    signal = pd.Series(0, index=values.index, dtype=int)
    signal.loc[values > threshold] = 1
    signal.loc[values < -threshold] = -1
    return signal

