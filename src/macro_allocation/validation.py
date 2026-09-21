"""Strict validation for configuration, source observations, and run lineage."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from .config import runtime_configuration_errors
from .data import SourceTables, parse_dates
from .errors import ConfigurationError, DataValidationError


PROHIBITED_SOURCE_WORDS = {"mock", "random", "demo", "synthetic", "placeholder", "fallback"}


def require_valid_runtime_config(config: dict[str, Any]) -> None:
    errors = runtime_configuration_errors(config)
    if errors:
        raise ConfigurationError("; ".join(errors))


def _duplicate_errors(frame: pd.DataFrame, keys: list[str], label: str) -> list[str]:
    missing = [key for key in keys if key not in frame.columns]
    if missing:
        return [f"{label} missing key fields: {','.join(missing)}"]
    if frame.duplicated(keys).any():
        return [f"{label} has duplicate keys: {','.join(keys)}"]
    return []


def audit_source_tables(
    sources: SourceTables, config: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    errors += _duplicate_errors(sources.asset_levels, ["date"], "asset_levels")
    errors += _duplicate_errors(sources.china_equity_level, ["date"], "china_equity_level")
    errors += _duplicate_errors(
        sources.domestic_macro, ["release_date", "indicator"], "domestic_macro"
    )
    errors += _duplicate_errors(
        sources.global_macro, ["release_date", "indicator"], "global_macro"
    )

    asset_frame = sources.asset_levels
    for asset, spec in config["assets"].items():
        column = spec["column"]
        if column not in asset_frame.columns:
            errors.append(f"asset_levels missing {column} for {asset}")
            continue
        dates = pd.to_datetime(asset_frame["date"], errors="coerce", format="mixed")
        values = pd.to_numeric(asset_frame[column], errors="coerce")
        monthly = pd.DataFrame({"date": dates, "value": values}).dropna(subset=["date"])
        counts = monthly.dropna(subset=["value"]).set_index("date")["value"].resample("YE").count()
        covered_years = int((counts >= 6).sum())
        sample_years = max(1, dates.dt.year.nunique())
        if covered_years < max(1, sample_years - 1):
            errors.append(
                f"{asset}/{column} has insufficient monthly frequency: "
                f"{int(values.notna().sum())} non-null source observations"
            )

    domestic = sources.domestic_macro
    for indicator in ("loan", "property_index"):
        values = domestic.loc[domestic.get("indicator") == indicator]
        nonnull = int(pd.to_numeric(values.get("value"), errors="coerce").notna().sum())
        if nonnull < 120:
            errors.append(
                f"domestic macro {indicator} has insufficient monthly history: {nonnull} observations"
            )

    for label, frame in {
        "asset_levels": sources.asset_levels,
        "china_equity_level": sources.china_equity_level,
        "domestic_macro": sources.domestic_macro,
        "global_macro": sources.global_macro,
    }.items():
        for column in frame.columns:
            if frame[column].dtype == object:
                sample = " ".join(frame[column].dropna().astype(str).head(100).str.lower())
                if any(word in sample for word in PROHIBITED_SOURCE_WORDS):
                    errors.append(f"{label} contains prohibited production source marker")
                    break
    return sorted(set(errors))


def require_valid_sources(sources: SourceTables, config: dict[str, Any]) -> None:
    errors = audit_source_tables(sources, config)
    if errors:
        raise DataValidationError("; ".join(errors))


def ensure_no_missing_weighted_returns(
    returns: pd.DataFrame, weights: pd.Series
) -> None:
    missing_keys = sorted(set(weights.index) - set(returns.columns))
    extra_keys = sorted(set(returns.columns) - set(weights.index))
    if missing_keys or extra_keys:
        raise DataValidationError(
            "portfolio and return columns differ: "
            f"missing={missing_keys or 'none'}, extra={extra_keys or 'none'}"
        )
    active = weights[weights.ne(0)].index
    missing = returns[active].isna()
    if missing.any().any():
        first = missing.stack()[lambda x: x].index[0]
        raise DataValidationError(
            f"missing asset return cannot be treated as zero: date={first[0].date()}, asset={first[1]}"
        )


def check_release_dates_not_after_signal(
    release_dates: pd.Series, signal_dates: pd.Series
) -> None:
    release = pd.to_datetime(release_dates, errors="coerce")
    signal = pd.to_datetime(signal_dates, errors="coerce")
    if release.isna().any() or signal.isna().any():
        raise DataValidationError("release/signal dates must be valid")
    if (release > signal).any():
        raise DataValidationError("look-ahead detected: release date is after signal date")


def assert_no_nested_git(project_root: Path) -> None:
    hits = [p for p in project_root.rglob(".git") if p != project_root / ".git"]
    if hits or (project_root / ".gitmodules").exists():
        raise ConfigurationError("nested .git or submodule metadata detected")
