"""Macro factor implementations extracted from the notebooks."""

from .autoregression import autoregressive_signal
from .domestic import build_domestic_signals
from .global_factors import build_global_signals

__all__ = ["autoregressive_signal", "build_domestic_signals", "build_global_signals"]

