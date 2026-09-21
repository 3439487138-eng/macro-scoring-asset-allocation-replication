from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from macro_allocation.config import (
    load_config,
    runtime_configuration_errors,
    validate_structure,
)


ROOT = Path(__file__).resolve().parents[1]


def test_base_config_structure_is_safe() -> None:
    config = load_config(ROOT / "config/base.yml")
    assert validate_structure(config) == []


def test_strict_config_detects_credit_short_bond_and_bond_semantics() -> None:
    errors = runtime_configuration_errors(load_config(ROOT / "config/base.yml"))
    combined = " ".join(errors)
    assert "CREDIT" in combined
    assert "SHORT_BOND" in combined
    assert "yield level" in combined
    assert "lag review is unresolved" in combined


def test_prohibited_provider_is_rejected() -> None:
    config = load_config(ROOT / "config/base.yml")
    unsafe = deepcopy(config)
    unsafe["data"]["provider"] = "synthetic_fallback"
    assert any("prohibited" in error for error in validate_structure(unsafe))


def test_absolute_input_path_is_rejected() -> None:
    config = load_config(ROOT / "config/base.yml")
    unsafe = deepcopy(config)
    unsafe["data"]["files"]["asset_levels"] = "C:" + "/private/data.csv"
    assert any("repository-relative" in error for error in validate_structure(unsafe))


@pytest.mark.parametrize("marker", ["mock", "random", "demo", "synthetic"])
def test_artificial_input_filename_is_rejected(marker: str) -> None:
    config = load_config(ROOT / "config/base.yml")
    unsafe = deepcopy(config)
    unsafe["data"]["files"]["asset_levels"] = f"{marker}_prices.csv"
    assert any("prohibited production marker" in error for error in validate_structure(unsafe))
