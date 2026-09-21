#!/usr/bin/env python3
"""Scan the explicit upload allowlist for secrets, paths, databases, and size."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yml", ".yaml", ".json", ".example", ".ipynb", ""}
PROHIBITED_SUFFIXES = {".pkl", ".pickle", ".db", ".sqlite", ".sqlite3"}
WINDOWS_BACKSLASH = "\\"
PATTERNS = {
    "Windows absolute path": re.compile(
        r"(?i)(?:[a-z]:" + re.escape(WINDOWS_BACKSLASH) + r"|[a-z]:/)"
    ),
    "Unix home path": re.compile(r"/(?:home|Users)/[^/\s]+/"),
    "credential assignment": re.compile(
        r"(?i)(?:api[_-]?key|access[_-]?token|password|passwd|cookie|authorization)\s*[:=]\s*['\"]?[^\s'\"]+"
    ),
    "bearer token": re.compile(r"(?i)bearer\s+[a-z0-9._-]{12,}"),
}


def text_for_scan(path: Path) -> str:
    content = path.read_text(encoding="utf-8")
    if path.suffix.lower() != ".ipynb":
        return content

    # Scan decoded notebook strings so escaped newlines after an identifier are
    # not mistaken for a drive-letter path. Outputs were removed by the sanitizer,
    # but all remaining strings (source and metadata included) are still scanned.
    notebook = json.loads(content)
    strings: list[str] = []

    def collect(value: object) -> None:
        if isinstance(value, str):
            strings.append(value)
        elif isinstance(value, list):
            for item in value:
                collect(item)
        elif isinstance(value, dict):
            for key, item in value.items():
                strings.append(str(key))
                collect(item)

    collect(notebook)
    return "\n".join(strings)


def load_candidates(path: Path) -> list[Path]:
    candidates = []
    for line in path.read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        candidate = Path(value)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError(f"candidate is not repository-relative: {value}")
        candidates.append(candidate)
    return candidates


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="docs/upload_candidates.txt")
    args = parser.parse_args()
    manifest = ROOT / args.manifest
    errors: list[str] = []
    try:
        candidates = load_candidates(manifest)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"ERROR: cannot load upload manifest ({type(exc).__name__})", file=sys.stderr)
        return 2
    if len(candidates) != len(set(candidates)):
        errors.append("candidate list contains duplicates")
    for relative in candidates:
        path = ROOT / relative
        if not path.is_file():
            errors.append(f"missing candidate: {relative.as_posix()}")
            continue
        if path.suffix.lower() in PROHIBITED_SUFFIXES:
            errors.append(f"prohibited database/pickle candidate: {relative.as_posix()}")
        if path.stat().st_size > 10 * 1024 * 1024:
            errors.append(f"candidate exceeds 10 MiB review threshold: {relative.as_posix()}")
        if path.suffix.lower() in TEXT_SUFFIXES or path.name in {".gitignore", ".env.example"}:
            try:
                content = text_for_scan(path)
            except (UnicodeError, json.JSONDecodeError):
                errors.append(f"candidate is not UTF-8 text: {relative.as_posix()}")
                continue
            for label, pattern in PATTERNS.items():
                if pattern.search(content):
                    errors.append(f"{label} in {relative.as_posix()}")
    nested = [p for p in ROOT.rglob(".git") if p != ROOT / ".git"]
    if nested or (ROOT / ".gitmodules").exists():
        errors.append("nested Git or submodule metadata detected")
    if errors:
        print("ERROR: " + "; ".join(sorted(set(errors))), file=sys.stderr)
        return 2
    print(f"Upload candidate scan passed: {len(candidates)} files")
    for relative in candidates:
        print(relative.as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
