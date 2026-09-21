"""Input and execution provenance helpers."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import pandas as pd


SKILL_SHA256 = "A086CE12A88874C66B1CE006169B343F2151552001B8B1E3BFB5E446CEA6260F"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_record(path: Path) -> dict[str, object]:
    frame = pd.read_csv(path)
    return {
        "name": path.name,
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "rows": len(frame),
        "columns": list(frame.columns),
        "license_status": "unconfirmed",
    }


def git_sha(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    return result.stdout.strip()

