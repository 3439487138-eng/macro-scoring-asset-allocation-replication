from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


FIXTURES = Path(__file__).parent / "fixtures"


def test_dotenv_does_not_override_ci_environment(monkeypatch) -> None:
    monkeypatch.setenv("FIXTURE_PRECEDENCE", "ci_value")
    load_dotenv(FIXTURES / "test.env")
    assert os.environ["FIXTURE_PRECEDENCE"] == "ci_value"

