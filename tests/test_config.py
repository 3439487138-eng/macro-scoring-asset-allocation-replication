from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from macro_allocation.config import (
    load_config,
    validate_structure,
)


ROOT = Path(__file__).resolve().parents[1]


def test_base_config_structure_is_safe() -> None:
    config = load_config(ROOT / "config/base.yml")
    assert validate_structure(config) == []


def test_credit_is_distinct_and_adjusted_price_based() -> None:
    config = load_config(ROOT / "config/base.yml")
    assert "CREDIT" in config["assets"]
    assert "SHORT_BOND" not in config["assets"]
    assert config["assets"]["CREDIT"]["symbol"] == "VCSH"
    assert "adjusted_close" in config["assets"]["CH_BOND"]["return_semantics"]


def test_prohibited_provider_is_rejected() -> None:
    config = load_config(ROOT / "config/base.yml")
    unsafe = deepcopy(config)
    unsafe["data"]["provider"] = "synthetic_fallback"
    assert any("prohibited" in error for error in validate_structure(unsafe))


def test_absolute_output_path_is_rejected() -> None:
    config = load_config(ROOT / "config/base.yml")
    unsafe = deepcopy(config)
    unsafe["outputs"]["directory"] = "C:" + "/private/outputs"
    assert any("repository-relative" in error for error in validate_structure(unsafe))


@pytest.mark.parametrize("marker", ["mock", "random", "demo", "synthetic"])
def test_artificial_provider_is_rejected(marker: str) -> None:
    config = load_config(ROOT / "config/base.yml")
    unsafe = deepcopy(config)
    unsafe["data"]["provider"] = f"{marker}_prices"
    assert validate_structure(unsafe)
