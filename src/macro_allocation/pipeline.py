"""End-to-end real-data pipeline. No legacy results are read."""

from __future__ import annotations

import json
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from .backtest import apply_one_period_lag, portfolio_returns
from .config import resolve_input_paths
from .data import china_monthly_return, load_sources, monthly_asset_returns
from .factors import autoregressive_signal, build_domestic_signals, build_global_signals
from .metrics import build_nav, compute_metrics
from .portfolio import build_asset_positions
from .provenance import SKILL_SHA256, git_sha, input_record
from .reporting import build_payload, render_report, save_equity_figure, write_json
from .validation import require_valid_runtime_config, require_valid_sources


def run_pipeline(config: dict[str, Any], project_root: Path, config_path: Path) -> list[Path]:
    # Every validation occurs before output creation.
    require_valid_runtime_config(config)
    paths = resolve_input_paths(config, project_root)
    sources = load_sources(paths)
    require_valid_sources(sources, config)

    start = config["project"]["sample_start"]
    end = config["project"]["sample_end"]
    initial = int(config["project"]["initial_window_months"])
    returns = monthly_asset_returns(sources.asset_levels, config["assets"], start, end)
    china_returns = china_monthly_return(sources.china_equity_level, start, end)

    domestic = build_domestic_signals(sources.domestic_macro, config["factors"], start, end, initial)
    global_signals = build_global_signals(sources.global_macro, config["factors"], start, end, initial)
    ar_cfg = config["factors"]["autoregression"]
    ar = autoregressive_signal(
        china_returns,
        lags=int(ar_cfg["lags"]),
        initial_window=int(ar_cfg["initial_window"]),
    )
    signals = pd.concat([domestic, global_signals, ar], axis=1).dropna().sort_index()
    positions = build_asset_positions(signals, config["factor_weights"])
    executed, asset_strategy_returns = apply_one_period_lag(
        positions, returns, int(config["project"]["signal_lag_months"])
    )
    strategy_returns = portfolio_returns(asset_strategy_returns, config["portfolio_weights"])
    nav = build_nav(strategy_returns)
    metrics = compute_metrics(strategy_returns)

    output_dir = project_root / config["outputs"]["directory"]
    approved = set(config["outputs"]["approved_files"])
    with tempfile.TemporaryDirectory(prefix=".macro-run-", dir=project_root) as temp_name:
        temp = Path(temp_name)
        nav.to_csv(temp / "nav.csv", index_label="date")
        executed.to_csv(temp / "positions.csv", index_label="date")
        signals.to_csv(temp / "factor_signals.csv", index_label="date")
        pd.DataFrame([metrics]).to_csv(temp / "metrics.csv", index=False)
        save_equity_figure(nav, temp / "equity_curve.png")

        now = datetime.now(timezone.utc).isoformat()
        inputs = [input_record(path) for path in paths.values()]
        run = {
            "status": "adapted",
            "mode": config["project"]["mode"],
            "sample": f"{metrics['period_start']} to {metrics['period_end']}",
            "generated_at": now,
            "commit_sha": git_sha(project_root),
            "command": f"python run_replication.py run --config {config_path.as_posix()}",
            "config": config_path.as_posix(),
        }
        payload = build_payload(metrics, run, inputs)
        write_json(payload, temp / "report.json")
        render_report(payload, temp / "equity_curve.png", temp / "report.html")
        manifest = {
            "status": "computed_from_current_run",
            "generated_at": now,
            "skill_sha256": SKILL_SHA256,
            "inputs": inputs,
            "approved_outputs": sorted(approved),
        }
        (temp / "run_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        produced = {path.name for path in temp.iterdir()}
        if not produced.issubset(approved):
            raise ValueError(f"pipeline produced unapproved outputs: {sorted(produced - approved)}")
        output_dir.mkdir(exist_ok=True)
        published: list[Path] = []
        for source in temp.iterdir():
            destination = output_dir / source.name
            shutil.copy2(source, destination)
            published.append(destination)
    return sorted(published)

