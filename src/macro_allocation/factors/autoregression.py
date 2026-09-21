"""Walk-forward autoregressive factor from the research notebook."""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.ar_model import AutoReg

from ..errors import DataValidationError, ReproductionIncomplete
from ..transforms import require_complete


def autoregressive_signal(
    returns: pd.Series, lags: int = 12, initial_window: int = 36
) -> pd.Series:
    series = returns.dropna().sort_index()
    require_complete(series, "autoregressive return history")
    if len(series) < initial_window:
        raise DataValidationError("insufficient observations for autoregression")
    forecasts: list[tuple[pd.Timestamp, float]] = []
    for end in range(initial_window, len(series) + 1):
        training = series.iloc[:end]
        try:
            model = AutoReg(training, lags=lags, old_names=False).fit()
            prediction = model.predict(start=len(training), end=len(training))
        except (ValueError, np.linalg.LinAlgError) as exc:
            raise ReproductionIncomplete(
                f"autoregression failed at {training.index[-1].date()}: {type(exc).__name__}"
            ) from exc
        forecasts.append((training.index[-1], float(prediction.iloc[0])))
    return pd.Series(dict(forecasts)).sort_index().apply(np.sign).rename("ar_signal")

