"""Configuration loading and strict practical-adaptation validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigurationError


PROHIBITED_MARKERS = {"mock", "random", "demo", "synthetic", "placeholder", "fallback"}
REQUIRED_TOP_LEVEL = {
    "project",
    "data",
    "assets",
    "cash",
    "macro_proxies",
    "factor_model",
    "factor_weights",
    "portfolio_weights",
    "outputs",
}


def load_config(path: Path) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigurationError(f"configuration file not found: {path.name}") from exc
    except yaml.YAMLError as exc:
        raise ConfigurationError(f"configuration is not valid YAML: {path.name}") from exc
    if not isinstance(payload, dict):
        raise ConfigurationError("configuration root must be a mapping")
    return payload


def validate_structure(config: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_TOP_LEVEL - set(config))
    if missing:
        return [f"missing top-level sections: {', '.join(missing)}"]

    project = config["project"]
    data = config["data"]
    if project.get("mode") != "practical_adaptation":
        errors.append("project.mode must explicitly be practical_adaptation")
    if int(project.get("signal_lag_months", -1)) != 1:
        errors.append("signal_lag_months must equal one")
    if float(project.get("transaction_cost_bps", -1)) < 0:
        errors.append("transaction_cost_bps must be non-negative")
    if data.get("provider") != "yahoo_chart_runtime":
        errors.append("only the declared yahoo_chart_runtime provider is allowed")
    provider_text = " ".join(str(value).lower() for value in data.values())
    if any(marker in provider_text for marker in PROHIBITED_MARKERS):
        errors.append("production data configuration contains a prohibited marker")

    asset_keys = set(config["assets"])
    weight_keys = set(config["portfolio_weights"])
    factor_keys = set(config["factor_weights"])
    if asset_keys != weight_keys or asset_keys != factor_keys:
        errors.append(
            "asset, portfolio-weight and factor-weight keys must match exactly "
            f"(assets={sorted(asset_keys)}, portfolio={sorted(weight_keys)}, factors={sorted(factor_keys)})"
        )
    if "SHORT_BOND" in asset_keys:
        errors.append("SHORT_BOND must not be silently aliased; the practical sleeve is CREDIT")
    if "CREDIT" not in asset_keys:
        errors.append("CREDIT practical-adaptation sleeve is required")

    symbols = [str(item.get("symbol", "")).strip() for item in config["assets"].values()]
    symbols += [str(config["cash"].get("symbol", "")).strip()]
    symbols += [str(item.get("symbol", "")).strip() for item in config["macro_proxies"].values()]
    if not all(symbols):
        errors.append("every asset, cash and macro proxy requires a symbol")
    if any(any(marker in symbol.lower() for marker in PROHIBITED_MARKERS) for symbol in symbols):
        errors.append("production symbol contains a prohibited marker")

    weights = {key: float(value) for key, value in config["portfolio_weights"].items()}
    if abs(sum(weights.values()) - 1.0) > 1e-12:
        errors.append("portfolio weights must sum to one")
    if any(value < 0 for value in weights.values()):
        errors.append("base portfolio weights must be non-negative")

    model = config["factor_model"]
    if int(model.get("fx_internal_lag_months", -1)) != 0:
        errors.append("FX internal lag must be zero; execution lag is applied once at portfolio level")
    if int(model.get("execution_lag_months", -1)) != 1:
        errors.append("factor_model.execution_lag_months must equal one")

    output_dir = Path(str(config["outputs"].get("directory", "")))
    if output_dir.is_absolute() or ".." in output_dir.parts:
        errors.append("outputs.directory must be repository-relative")
    approved = [Path(str(item)) for item in config["outputs"].get("approved_files", [])]
    if not approved or len(approved) != len(set(approved)):
        errors.append("outputs.approved_files must be a non-empty unique list")
    for item in approved:
        if item.is_absolute() or ".." in item.parts:
            errors.append(f"approved output is not repository-relative: {item.as_posix()}")
    return errors


def require_valid_config(config: dict[str, Any]) -> None:
    errors = validate_structure(config)
    if errors:
        raise ConfigurationError("; ".join(errors))


def output_paths(config: dict[str, Any], project_root: Path) -> list[Path]:
    root = (project_root / str(config["outputs"]["directory"])).resolve()
    return [(root / str(relative)).resolve() for relative in config["outputs"]["approved_files"]]
