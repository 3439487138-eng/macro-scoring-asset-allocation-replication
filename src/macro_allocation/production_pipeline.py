"""End-to-end production pipeline. Legacy outputs are never read."""
from __future__ import annotations
import json, shutil, tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import pandas as pd
from .portfolio import build_asset_positions
from .practical_factors import build_asset_returns, build_macro_scores, monthly_prices
from .production_backtest import run_backtest
from .production_metrics import build_nav, compute_metrics
from .production_reporting import build_payload, save_figures, write_markdown, write_report
from .provenance import git_sha
from .yahoo_provider import download_market_data

def run_pipeline(config: dict[str,Any], project_root: Path, config_path: Path) -> list[Path]:
    market=download_market_data(config,project_root)
    prices=monthly_prices(market.daily,config["data"]["as_of_date"])
    scores=build_macro_scores(prices,config)
    signal_columns=[c for c in scores if c.endswith("_signal")]
    positions=build_asset_positions(scores[signal_columns],config["factor_weights"])
    asset_returns,cash_returns=build_asset_returns(prices,config)
    result=run_backtest(positions,asset_returns,cash_returns,config["portfolio_weights"],float(config["project"]["transaction_cost_bps"]),config["project"]["sample_start"],market.daily,{a:s["symbol"] for a,s in config["assets"].items()})
    nav=build_nav(result.monthly)
    metrics=compute_metrics(result.monthly,config["data"]["as_of_date"],float(config["project"]["risk_free_rate"]))
    output_dir=project_root/config["outputs"]["directory"]; approved=set(config["outputs"]["approved_files"])
    output_dir.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".macro-run-",dir=output_dir) as name:
        temp=Path(name); (temp/"figures").mkdir()
        pd.DataFrame([metrics]).to_csv(temp/"performance_metrics.csv",index=False)
        result.monthly.to_csv(temp/"monthly_returns.csv",index_label="date")
        nav.to_csv(temp/"nav_curve.csv",index_label="date")
        result.allocations.to_csv(temp/"allocation_weights.csv",index_label="date")
        asset_returns.reindex(result.monthly.index).assign(CASH=cash_returns.reindex(result.monthly.index)).to_csv(temp/"asset_returns.csv",index_label="date")
        scores.reindex(positions.index).to_csv(temp/"macro_scores.csv",index_label="signal_date")
        result.rebalance.to_csv(temp/"rebalance_records.csv",index=False)
        market.duplicates.to_csv(temp/"duplicate_records.csv",index=False)
        manifest={"generated_at":datetime.now(timezone.utc).isoformat(),"provider":config["data"]["provider"],"raw_redistribution":False,"inputs":market.manifest}
        (temp/"input_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding="utf-8")
        figures=save_figures(nav,result.allocations,temp/"figures")
        run={"status":"adapted","mode":config["project"]["mode"],"sample":f"{metrics['backtest_start']} to {metrics['backtest_end']}","generated_at":manifest["generated_at"],"commit_sha":git_sha(project_root),"command":f"python run_replication.py --config {config_path.as_posix()}","config":config_path.as_posix()}
        assets=[{"asset":a,"symbol":str(s["symbol"]),"role":str(s["role"])} for a,s in config["assets"].items()]
        payload=build_payload(metrics,run,assets,market.manifest)
        write_report(payload,figures,temp/"report.json",temp/"report.html"); write_markdown(payload,temp/"backtest_report.md")
        produced={p.relative_to(temp).as_posix() for p in temp.rglob("*") if p.is_file()}
        if produced != approved: raise ValueError(f"output allowlist mismatch: missing={sorted(approved-produced)}, extra={sorted(produced-approved)}")
        for rel in approved:
            dest=output_dir/rel; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(temp/rel,dest)
    return sorted(output_dir/rel for rel in approved)
