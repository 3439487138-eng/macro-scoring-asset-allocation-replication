#!/usr/bin/env python3
"""Validate report structure; this does not prove that a backtest is correct."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


SECTIONS = [
    "Executive Summary",
    "Headline Metrics",
    "Figures and Result Tables",
    "Methodology Mapping",
    "Data and Assumptions",
    "Fidelity Gaps and Limitations",
    "Reproducibility",
]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", default="outputs/report.html")
    parser.add_argument("--payload", default="outputs/report.json")
    args = parser.parse_args()
    report = Path(args.report)
    payload_path = Path(args.payload)
    if not report.is_file() or not payload_path.is_file():
        print("ERROR: current-run report and payload are required", file=sys.stderr)
        return 2
    try:
        payload = json.loads(payload_path.read_text(encoding="utf-8"))
        document = report.read_text(encoding="utf-8")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        print(f"ERROR: cannot read report ({type(exc).__name__})", file=sys.stderr)
        return 2
    missing = [section for section in SECTIONS if section not in document]
    required = {"paper", "run", "summary", "metrics", "methodology", "assumptions", "fidelity_gaps"}
    missing_keys = sorted(required - set(payload))
    if missing or missing_keys or "data:image/png;base64," not in document:
        print(
            f"ERROR: report contract failed; sections={missing}, keys={missing_keys}",
            file=sys.stderr,
        )
        return 2
    if payload["run"].get("status") not in {"matched", "adapted", "extended"}:
        print("ERROR: report status is not publishable", file=sys.stderr)
        return 2
    print("Report structure validation passed; financial execution must be verified separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

