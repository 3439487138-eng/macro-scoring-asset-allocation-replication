#!/usr/bin/env python3
"""Build portable manifests for local inputs and legacy_unverified evidence."""

from __future__ import annotations

import hashlib
import json
import argparse
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
CORE = [
    "China Rolled Return.csv",
    "China Rolled Return2.csv",
    "china-data.csv",
    "data_indicator_review.csv",
]
LEGACY = [
    "mutiple_assets.ipynb",
    "single_assets.ipynb",
    "Macro Independent China/Independent_Review_China_edited.ipynb",
    "Trend to Return.xlsx",
    "Trend to Return_adjustposition.xlsx",
    "all_signal.csv",
    "annual_statistics.csv",
    "asset_positions.csv",
    "asset_strategies.csv",
    "df_pos.csv",
    "dom_credit_factor.csv",
    "dom_econ_factor.csv",
    "dom_econ_factor_trend.csv",
    "dom_econ_factor_with_benchmark.csv",
    "monthly_data.csv",
    "portfolio_strategy.csv",
    "multi_asset_performance.png",
    "em_eq_fut.pkl",
]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def csv_record(path: Path) -> dict[str, object]:
    frame = pd.read_csv(path)
    coverage: dict[str, object] = {}
    for field in ("date", "release_date"):
        if field in frame.columns:
            dates = pd.to_datetime(frame[field], errors="coerce", format="mixed")
            coverage = {
                "date_field": field,
                "valid_dates": int(dates.notna().sum()),
                "start": dates.min().date().isoformat() if dates.notna().any() else None,
                "end": dates.max().date().isoformat() if dates.notna().any() else None,
            }
            break
    return {
        "path": path.name,
        "sha256": sha256(path),
        "bytes": path.stat().st_size,
        "rows": len(frame),
        "columns": list(frame.columns),
        "coverage": coverage,
        "source": "user-supplied local file; original provider unconfirmed",
        "license_status": "unconfirmed_do_not_upload",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "docs",
        help="manifest destination (default: project docs directory)",
    )
    args = parser.parse_args()
    docs = args.output_dir.resolve()
    docs.mkdir(exist_ok=True)
    data_records = [csv_record(ROOT / name) for name in CORE]
    legacy_records = []
    purposes = {
        ".ipynb": "research source with unverified embedded outputs",
        ".xlsx": "historical spreadsheet result",
        ".csv": "historical derived result",
        ".png": "historical figure",
        ".pkl": "unused unsafe binary; not deserialized",
    }
    for name in LEGACY:
        path = ROOT / name
        legacy_records.append(
            {
                "path": name.replace("\\", "/"),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
                "status": "legacy_unverified",
                "purpose": purposes.get(path.suffix.lower(), "historical evidence"),
                "production_read_allowed": False,
            }
        )
    (docs / "data_manifest.json").write_text(
        json.dumps({"status": "license_unconfirmed", "files": data_records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (docs / "legacy_manifest.json").write_text(
        json.dumps({"status": "legacy_unverified", "files": legacy_records}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(data_records)} data and {len(legacy_records)} legacy records.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
