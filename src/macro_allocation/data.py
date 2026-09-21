"""Load only declared real source observations and align them by release date."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .errors import DataValidationError


LEGACY_NAMES = {
    "all_signal.csv",
    "annual_statistics.csv",
    "asset_positions.csv",
    "asset_strategies.csv",
    "df_pos.csv",
    "dom_credit_factor.csv",
    "dom_econ_factor.csv",
    "dom_econ_factor_trend.csv",
    "dom_econ_factor_with_benchmark.csv",
    "monthly_data.csv",
    "portfolio_strategy.csv",
}
PROHIBITED_PATH_PARTS = {"outputs", "artifacts", "notebooks", "fixtures"}


@dataclass(frozen=True)
class SourceTables:
    asset_levels: pd.DataFrame
    china_equity_level: pd.DataFrame
    domestic_macro: pd.DataFrame
    global_macro: pd.DataFrame


def _read_csv(path: Path, label: str) -> pd.DataFrame:
    if path.name in LEGACY_NAMES or any(part.lower() in PROHIBITED_PATH_PARTS for part in path.parts):
        raise DataValidationError(f"production input {label} points to prohibited legacy/test path")
    if not path.is_file():
        raise DataValidationError(f"required real input is missing: {path.name}")
    try:
        frame = pd.read_csv(path)
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        raise DataValidationError(f"cannot read real input {path.name}: {type(exc).__name__}") from exc
    if frame.empty:
        raise DataValidationError(f"required real input is empty: {path.name}")
    return frame


def load_sources(paths: dict[str, Path]) -> SourceTables:
    return SourceTables(
        asset_levels=_read_csv(paths["asset_levels"], "asset_levels"),
        china_equity_level=_read_csv(paths["china_equity_level"], "china_equity_level"),
        domestic_macro=_read_csv(paths["domestic_macro"], "domestic_macro"),
        global_macro=_read_csv(paths["global_macro"], "global_macro"),
    )


def parse_dates(frame: pd.DataFrame, column: str, label: str) -> pd.DataFrame:
    if column not in frame.columns:
        raise DataValidationError(f"{label} is missing date field {column}")
    result = frame.copy()
    parsed = pd.to_datetime(result[column], errors="coerce", format="mixed")
    if parsed.isna().any():
        raise DataValidationError(f"{label} contains invalid dates in {column}")
    result[column] = parsed
    return result


def monthly_asset_returns(
    asset_levels: pd.DataFrame,
    assets: dict[str, dict[str, Any]],
    start: str,
    end: str,
) -> pd.DataFrame:
    frame = parse_dates(asset_levels, "date", "asset_levels")
    frame = frame.sort_values("date").set_index("date")
    output: dict[str, pd.Series] = {}
    for asset, spec in assets.items():
        column = spec["column"]
        if column not in frame.columns:
            raise DataValidationError(f"asset_levels is missing column {column} for {asset}")
        level = pd.to_numeric(frame[column], errors="coerce")
        monthly = level.resample("ME").last()
        output[asset] = monthly.pct_change(fill_method=None)
    return pd.DataFrame(output).loc[start:end]


def china_monthly_return(frame: pd.DataFrame, start: str, end: str) -> pd.Series:
    data = parse_dates(frame, "date", "china_equity_level")
    if "China" not in data.columns:
        raise DataValidationError("china_equity_level is missing column China")
    series = pd.to_numeric(data.set_index("date")["China"], errors="coerce").sort_index()
    return series.resample("ME").last().pct_change(fill_method=None).loc[start:end]


def monthly_macro_panel(
    frame: pd.DataFrame,
    indicators: list[str],
    start: str,
    end: str,
    label: str,
) -> pd.DataFrame:
    data = parse_dates(frame, "release_date", label)
    required = {"indicator", "value"}
    if not required.issubset(data.columns):
        raise DataValidationError(f"{label} must contain release_date, indicator, value")
    subset = data[data["indicator"].isin(indicators)].copy()
    absent = sorted(set(indicators) - set(subset["indicator"].unique()))
    if absent:
        raise DataValidationError(f"{label} is missing indicators: {', '.join(absent)}")
    if subset.duplicated(["release_date", "indicator"]).any():
        raise DataValidationError(f"{label} contains duplicate release_date/indicator keys")
    subset["value"] = pd.to_numeric(subset["value"], errors="coerce")
    decision_dates = subset["release_date"].dt.to_period("M").dt.to_timestamp("M")
    if (subset["release_date"] > decision_dates).any():
        raise DataValidationError(f"{label} contains a release after its month-end signal date")
    panel = subset.pivot(index="release_date", columns="indicator", values="value")
    return panel.sort_index().resample("ME").last().loc[start:end]


def asof_values(
    observations: pd.DataFrame, decision_dates: pd.DatetimeIndex
) -> pd.DataFrame:
    """Align already-observed values without inventing missing raw observations."""
    if not observations.index.is_monotonic_increasing:
        raise DataValidationError("macro release dates must be sorted")
    if observations.index.has_duplicates:
        raise DataValidationError("macro release dates must be unique after pivoting")
    # This operation selects the latest actual release at each decision date. It
    # does not fill blank observations inside a released record.
    left = pd.DataFrame({"decision_date": decision_dates}).sort_values("decision_date")
    right = observations.reset_index().rename(columns={observations.index.name or "index": "release_date"})
    return pd.merge_asof(
        left,
        right.sort_values("release_date"),
        left_on="decision_date",
        right_on="release_date",
        direction="backward",
        allow_exact_matches=True,
    ).set_index("decision_date")
