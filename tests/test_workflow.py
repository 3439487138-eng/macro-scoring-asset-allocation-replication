from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_workflow_is_manual_only_and_has_opt_in_real_run() -> None:
    text = (ROOT / ".github/workflows/paper-replication.yml").read_text(encoding="utf-8")
    assert "workflow_dispatch:" in text
    assert "run_replication:" in text
    assert "schedule:" not in text
    assert "pull_request:" not in text
    assert "repository_dispatch:" not in text
    assert "git add --all" not in text
    assert "configure-pages" not in text
    assert "deploy-pages" not in text
    assert "smtp" not in text.lower()
    assert "git add -- outputs/report.json" in text
    assert "contents: read" in text
    assert "replicate:" in text
    assert "if: ${{ inputs.run_replication }}" in text
    assert "needs: validate" in text
