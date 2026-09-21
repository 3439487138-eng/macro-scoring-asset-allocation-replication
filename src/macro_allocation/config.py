"""Configuration loading and repository-relative path resolution."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigurationError


PROHIBITED_PROVIDERS = {"mock", "random", "demo", "synthetic", "fallback"}
REQUIRED_TOP_LEVEL = {
    "project",
    "data",
    "assets",
    "factors",
    "factor_weights",
    "portfolio_weights",
    "outputs",
}


def load_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"configuration file not found: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"configuration is not valid YAML: {path.name}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("configuration root must be a mapping")
    return payload


def validate_structure(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - set(config))
    if missing:
        errors.append(f"missing top-level sections: {', '.join(missing)}")

    provider = str(config.get("data", {}).get("provider", "")).lower()
    if not provider:
        errors.append("data.provider is required")
    if any(token in provider for token in PROHIBITED_PROVIDERS):
        errors.append(f"prohibited production data provider: {provider}")

    files = config.get("data", {}).get("files", {})
    for key, value in files.items():
        candidate = Path(str(value))
        if candidate.is_absolute() or ".." in candidate.parts:
            errors.append(f"data.files.{key} must be a repository-relative filename")
        lowered = candidate.as_posix().lower()
        if any(token in lowered for token in PROHIBITED_PROVIDERS):
            errors.append(f"data.files.{key} contains a prohibited production marker")

    if config.get("project", {}).get("signal_lag_months") != 1:
        errors.append("the preserved strategy requires signal_lag_months=1")

    approved = config.get("outputs", {}).get("approved_files", [])
    if not approved or len(approved) != len(set(approved)):
        errors.append("outputs.approved_files must be a non-empty unique list")
    for name in approved:
        if Path(str(name)).is_absolute() or len(Path(str(name)).parts) != 1:
            errors.append(f"approved output must be a plain filename: {name}")
    return errors


def runtime_configuration_errors(config: dict[str, Any]) -> list[str]:
    errors = validate_structure(config)
    asset_keys = set(config.get("assets", {}))
    portfolio_keys = set(config.get("portfolio_weights", {}))
    if asset_keys != portfolio_keys:
        missing_returns = sorted(portfolio_keys - asset_keys)
        unused_returns = sorted(asset_keys - portfolio_keys)
        detail = []
        if missing_returns:
            detail.append("weights without return assets=" + ",".join(missing_returns))
        if unused_returns:
            detail.append("return assets without weights=" + ",".join(unused_returns))
        errors.append("portfolio/return asset keys differ (" + "; ".join(detail) + ")")

    for asset, spec in config.get("assets", {}).items():
        if spec.get("return_semantics") == "yield_level":
            errors.append(
                f"{asset} is declared as a yield level and cannot be treated as total return"
            )

    fx = config.get("factors", {}).get("domestic_fx", {})
    if fx.get("internal_lag_months", 0) and fx.get("lag_review_status") != "confirmed":
        errors.append(
            "domestic FX has an internal lag plus the portfolio lag; lag review is unresolved"
        )
    return errors


def resolve_data_root(config: dict[str, Any], project_root: Path) -> Path:
    env_name = config.get("data", {}).get("root_env", "MACRO_STRATEGY_DATA_DIR")
    override = os.environ.get(str(env_name), "").strip()
    return Path(override).expanduser().resolve() if override else project_root.resolve()


def resolve_input_paths(
    config: dict[str, Any], project_root: Path
) -> dict[str, Path]:
    data_root = resolve_data_root(config, project_root)
    return {
        key: (data_root / str(relative)).resolve()
        for key, relative in config["data"]["files"].items()
    }
