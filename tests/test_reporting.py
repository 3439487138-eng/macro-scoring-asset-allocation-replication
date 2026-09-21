from __future__ import annotations

from pathlib import Path

from macro_allocation.reporting import build_payload, render_report, write_json


def test_report_is_self_contained_and_escaped(tmp_path: Path) -> None:
    payload = build_payload(
        {"annualized_return": 0.1},
        {
            "status": "adapted",
            "mode": "strict",
            "sample": "2020-01-01 to 2020-12-31",
            "generated_at": "2020-12-31T00:00:00Z",
            "commit_sha": "abc",
            "command": "test command",
            "config": "tests/fixtures/config.yml",
        },
        [],
    )
    payload["summary"] = "<script>alert(1)</script>"
    figure = tmp_path / "figure.png"
    figure.write_bytes(b"not-a-production-image")
    html_path = tmp_path / "report.html"
    json_path = tmp_path / "report.json"
    write_json(payload, json_path)
    render_report(payload, figure, html_path)
    document = html_path.read_text(encoding="utf-8")
    assert "data:image/png;base64," in document
    assert "<script>alert(1)</script>" not in document
    assert "&lt;script&gt;" in document

