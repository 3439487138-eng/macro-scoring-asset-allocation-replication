from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from macro_allocation.config import load_config
from macro_allocation.data import SourceTables, _read_csv, monthly_macro_panel
from macro_allocation.errors import ConfigurationError, DataValidationError
from macro_allocation.validation import assert_no_nested_git, audit_source_tables


FIXTURES = Path(__file__).parent / "fixtures"


def test_duplicate_macro_key_is_fatal() -> None:
    frame = pd.read_csv(FIXTURES / "duplicate_macro.csv")
    with pytest.raises(DataValidationError, match="duplicate"):
        monthly_macro_panel(frame, ["x"], "2020-01-01", "2020-12-31", "fixture_macro")


def test_production_cannot_read_test_fixture() -> None:
    with pytest.raises(DataValidationError, match="prohibited"):
        _read_csv(FIXTURES / "duplicate_macro.csv", "fixture")


def test_production_cannot_read_legacy_result_name(tmp_path: Path) -> None:
    legacy = tmp_path / "portfolio_strategy.csv"
    legacy.write_text("date,return\n2020-01-01,0.1\n", encoding="utf-8")
    with pytest.raises(DataValidationError, match="prohibited"):
        _read_csv(legacy, "legacy")


def test_oil_and_loan_frequency_are_fatal() -> None:
    sources = SourceTables(
        asset_levels=pd.read_csv(FIXTURES / "frequency_asset_levels.csv"),
        china_equity_level=pd.read_csv(FIXTURES / "frequency_china_equity.csv"),
        domestic_macro=pd.read_csv(FIXTURES / "frequency_domestic_macro.csv"),
        global_macro=pd.read_csv(FIXTURES / "frequency_global_macro.csv"),
    )
    config = load_config(Path(__file__).parents[1] / "config/base.yml")
    config["assets"] = {"OIL": {"column": "oil"}}
    errors = audit_source_tables(sources, config)
    assert any("OIL/oil has insufficient monthly frequency" in error for error in errors)
    assert any("domestic macro loan has insufficient monthly history" in error for error in errors)


def test_submodule_metadata_is_fatal(tmp_path: Path) -> None:
    (tmp_path / ".gitmodules").write_text("[submodule 'x']\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="submodule"):
        assert_no_nested_git(tmp_path)
