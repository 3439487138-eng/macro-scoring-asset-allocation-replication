"""Self-contained report generation for a successfully computed current run."""

from __future__ import annotations

import base64
import html
import io
import json
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from jinja2 import BaseLoader, Environment, select_autoescape


HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>{{ title }}</title>
<style>body{font-family:Arial,sans-serif;max-width:1180px;margin:2rem auto;padding:0 1rem;color:#17202a}
table{border-collapse:collapse;width:100%;margin:1rem 0}th,td{border:1px solid #ccd1d1;padding:.45rem;text-align:left}
th{background:#eef2f3}.status{padding:.6rem;background:#e8f6f3;border-left:4px solid #148f77}
img{max-width:100%;height:auto}code{background:#f4f6f7;padding:.1rem .25rem}</style></head><body>
<h1>{{ title }}</h1><p class="status">Status: {{ run.status }} — {{ summary }}</p>
<h2>Executive Summary</h2><p>Mode: {{ run.mode }}. Sample: {{ run.sample }}. This is research output, not investment advice.</p>
<h2>Headline Metrics</h2><table><tr><th>Metric</th><th>Current run</th><th>Benchmark</th></tr>
{% for row in metrics %}<tr><td>{{ row.Metric }}</td><td>{{ row["Current run"] }}</td><td>{{ row.Benchmark }}</td></tr>{% endfor %}</table>
<h2>Figures and Result Tables</h2><img src="data:image/png;base64,{{ figure_data }}" alt="Strategy NAV and drawdown">
<h2>Methodology Mapping</h2><table><tr><th>Strategy rule</th><th>Implementation</th><th>Status</th></tr>
{% for row in methodology %}<tr><td>{{ row["Strategy rule"] }}</td><td>{{ row.Implementation }}</td><td>{{ row.Status }}</td></tr>{% endfor %}</table>
<h2>Data and Assumptions</h2><ul>{% for item in assumptions %}<li>{{ item }}</li>{% endfor %}</ul>
<h2>Fidelity Gaps and Limitations</h2><ul>{% for item in fidelity_gaps %}<li>{{ item }}</li>{% endfor %}</ul>
<h2>Reproducibility</h2><p>Commit: <code>{{ run.commit_sha }}</code><br>Generated: {{ run.generated_at }}<br>Command: <code>{{ run.command }}</code><br>Configuration: <code>{{ run.config }}</code></p>
</body></html>"""


def _format_metric(value: Any) -> str:
    if value is None:
        return "unavailable"
    if isinstance(value, float):
        return f"{value:.8g}"
    return str(value)


def save_equity_figure(nav: pd.DataFrame, path: Path) -> None:
    fig, axes = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
    axes[0].plot(nav.index, nav["strategy_nav"], label="Strategy")
    axes[0].set_title("Strategy equity curve")
    axes[0].set_ylabel("NAV")
    axes[0].grid(alpha=0.3)
    axes[0].legend()
    axes[1].fill_between(nav.index, nav["drawdown"], 0, color="#c0392b", alpha=0.35)
    axes[1].set_title("Drawdown from running peak")
    axes[1].set_ylabel("Drawdown")
    axes[1].grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)


def build_payload(
    metrics: dict[str, Any], run: dict[str, Any], inputs: list[dict[str, Any]]
) -> dict[str, Any]:
    metric_rows = [
        {"Metric": key, "Current run": _format_metric(value), "Benchmark": "unavailable"}
        for key, value in metrics.items()
    ]
    return {
        "paper": {
            "title": "Asset Allocation Macro Scoring Strategy",
            "citation": "Existing project, engineering extraction",
            "source": "sanitized research notebooks",
        },
        "run": run,
        "summary": "The report was generated from this run's validated real inputs and computations.",
        "metrics": metric_rows,
        "methodology": [
            {"Strategy rule": "Macro factor formulas", "Implementation": "Extracted into domestic/global modules", "Status": "adapted"},
            {"Strategy rule": "Asset-specific factor directions", "Implementation": "Configured without changing weights", "Status": "matched"},
            {"Strategy rule": "One-period execution lag", "Implementation": "Positions shifted exactly once", "Status": "matched"},
            {"Strategy rule": "Benchmark", "Implementation": "No benchmark was specified", "Status": "unavailable"},
        ],
        "assumptions": [
            "Monthly frequency; risk-free rate is zero for Sharpe ratio.",
            "Transaction costs remain zero because the legacy strategy did not implement them.",
            f"Validated input files: {len(inputs)}; all are user-supplied local observations.",
        ],
        "fidelity_gaps": [
            "Input redistribution licenses and original providers remain unconfirmed.",
            "Historical notebook/CSV/PNG/XLSX results are legacy_unverified and were not read.",
            "Test fixtures are isolated and are not evidence of strategy reproduction.",
        ],
        "inputs": inputs,
    }


def render_report(payload: dict[str, Any], figure_path: Path, output: Path) -> None:
    figure_data = base64.b64encode(figure_path.read_bytes()).decode("ascii")
    environment = Environment(loader=BaseLoader(), autoescape=select_autoescape(["html"]))
    rendered = environment.from_string(HTML_TEMPLATE).render(
        title=payload["paper"]["title"], figure_data=figure_data, **payload
    )
    output.write_text(rendered, encoding="utf-8")


def write_json(payload: dict[str, Any], output: Path) -> None:
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

