#!/usr/bin/env python3
"""Remove only the explicit generated-output allowlist before a fresh run."""
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
cfg=yaml.safe_load((ROOT/"config/base.yml").read_text(encoding="utf-8"))
root=ROOT/cfg["outputs"]["directory"]
for relative in cfg["outputs"]["approved_files"]:
    path=root/relative
    if path.is_file(): path.unlink()
print("Approved old outputs removed; local legacy evidence was untouched.")
