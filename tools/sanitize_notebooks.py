#!/usr/bin/env python3
"""Create upload-safe research-source copies without changing local originals."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    ROOT / "mutiple_assets.ipynb": ROOT / "notebooks/legacy/multi_asset_research.ipynb",
    ROOT / "single_assets.ipynb": ROOT / "notebooks/legacy/single_asset_research.ipynb",
    ROOT / "Macro Independent China/Independent_Review_China_edited.ipynb": ROOT
    / "notebooks/legacy/china_review_research.ipynb",
}
WINDOWS_PATH = re.compile(r"(?i)[a-z]:\\[^\s\"']+")


def main() -> int:
    for source, destination in SOURCES.items():
        notebook = json.loads(source.read_text(encoding="utf-8"))
        for cell in notebook.get("cells", []):
            cell["source"] = [WINDOWS_PATH.sub("[LOCAL_PATH_REMOVED]", line) for line in cell.get("source", [])]
            cell["outputs"] = []
            cell["execution_count"] = None
            cell.pop("attachments", None)
            cell["metadata"] = {}
        notebook["metadata"] = {
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.12"},
        }
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(notebook, ensure_ascii=False, indent=1), encoding="utf-8")
        print(destination.relative_to(ROOT).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

