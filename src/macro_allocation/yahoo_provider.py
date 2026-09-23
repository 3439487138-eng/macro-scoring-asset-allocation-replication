"""Yahoo chart endpoint adapter with strict validation and run-local caching."""

from __future__ import annotations

import hashlib
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

import pandas as pd
import requests

from .errors import DataValidationError


@dataclass(frozen=True)
class DownloadedMarketData:
    daily: dict[str, pd.Series]
    manifest: list[dict[str, Any]]
    duplicates: pd.DataFrame


def _epoch(value: str, extra_days: int = 0) -> int:
    stamp = pd.Timestamp(value, tz="UTC") + pd.Timedelta(days=extra_days)
    return int(stamp.timestamp())


def _cache_name(symbol: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", symbol).strip("_")
    return value or "symbol"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def parse_chart_response(symbol: str, payload: dict[str, Any]) -> pd.DataFrame:
    chart = payload.get("chart", {})
    if chart.get("error"):
        description = chart["error"].get("description", "provider error")
        raise DataValidationError(f"Yahoo returned an error for {symbol}: {description}")
    results = chart.get("result") or []
    if len(results) != 1:
        raise DataValidationError(f"Yahoo returned no unambiguous result for {symbol}")
    result = results[0]
    timestamps = result.get("timestamp") or []
    adjusted_blocks = result.get("indicators", {}).get("adjclose") or []
    if not timestamps or len(adjusted_blocks) != 1:
        raise DataValidationError(f"Yahoo response lacks adjusted close for {symbol}")
    values = adjusted_blocks[0].get("adjclose") or []
    if len(timestamps) != len(values):
        raise DataValidationError(f"Yahoo timestamp/value length mismatch for {symbol}")
    dates = pd.to_datetime(timestamps, unit="s", utc=True).tz_convert(None).normalize()
    frame = pd.DataFrame({"date": dates, "adjusted_close": values})
    frame["adjusted_close"] = pd.to_numeric(frame["adjusted_close"], errors="coerce")
    if frame["date"].duplicated().any():
        raise DataValidationError(f"Yahoo returned duplicate dates for {symbol}")
    if frame["adjusted_close"].notna().sum() < 100:
        raise DataValidationError(f"Yahoo returned insufficient real observations for {symbol}")
    frame["symbol"] = symbol
    frame["source"] = "Yahoo Finance chart endpoint"
    return frame.sort_values("date").reset_index(drop=True)


def _download_one(
    symbol: str,
    base_url: str,
    start: str,
    end: str,
    timeout: int,
    attempts: int,
) -> tuple[pd.DataFrame, str]:
    url = (
        f"{base_url.rstrip('/')}/{quote(symbol, safe='')}"
        f"?period1={_epoch(start)}&period2={_epoch(end, 1)}"
        "&interval=1d&events=div%2Csplits"
    )
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0 macro-allocation-research/1.0"},
                timeout=timeout,
            )
            response.raise_for_status()
            return parse_chart_response(symbol, response.json()), url
        except (requests.RequestException, json.JSONDecodeError, DataValidationError) as exc:
            last_error = exc
            if attempt < attempts:
                time.sleep(float(attempt) * 2.0)
    raise DataValidationError(
        f"cannot download validated real observations for {symbol}: {type(last_error).__name__}"
    ) from last_error


def download_market_data(config: dict[str, Any], project_root: Path) -> DownloadedMarketData:
    data_cfg = config["data"]
    symbols = {spec["symbol"] for spec in config["assets"].values()}
    symbols.add(config["cash"]["symbol"])
    symbols.update(spec["symbol"] for spec in config["macro_proxies"].values())
    cache = (project_root / data_cfg["cache_directory"]).resolve()
    if project_root.resolve() not in cache.parents:
        raise DataValidationError("data cache must stay inside the project")
    cache.mkdir(parents=True, exist_ok=True)

    downloaded: dict[str, tuple[pd.DataFrame, str]] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(symbols))) as executor:
        futures = {
            executor.submit(
                _download_one,
                symbol,
                str(data_cfg["base_url"]),
                str(data_cfg["download_start"]),
                str(data_cfg["as_of_date"]),
                int(data_cfg["timeout_seconds"]),
                int(data_cfg["max_attempts"]),
            ): symbol
            for symbol in sorted(symbols)
        }
        for future in as_completed(futures):
            symbol = futures[future]
            downloaded[symbol] = future.result()

    daily: dict[str, pd.Series] = {}
    records: list[dict[str, Any]] = []
    duplicate_rows: list[dict[str, Any]] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()
    cutoff = pd.Timestamp(data_cfg["as_of_date"])
    for symbol in sorted(downloaded):
        frame, url = downloaded[symbol]
        frame = frame.loc[frame["date"] <= cutoff].copy()
        duplicate_count = int(frame.duplicated(["date", "symbol"]).sum())
        if duplicate_count:
            duplicate_rows.append(
                {"source": "Yahoo Finance chart endpoint", "symbol": symbol, "duplicates": duplicate_count}
            )
            raise DataValidationError(f"duplicate provider dates detected for {symbol}")
        cache_path = cache / f"{_cache_name(symbol)}.csv"
        frame.to_csv(cache_path, index=False)
        clean = frame.dropna(subset=["adjusted_close"])
        series = clean.set_index("date")["adjusted_close"].astype(float).sort_index()
        if series.index.max() < cutoff - pd.Timedelta(days=10):
            raise DataValidationError(f"stale provider data for {symbol}")
        daily[symbol] = series
        records.append(
            {
                "symbol": symbol,
                "source": "Yahoo Finance chart endpoint",
                "request_url": url,
                "retrieved_at": retrieved_at,
                "path": cache_path.relative_to(project_root).as_posix(),
                "sha256": _sha256(cache_path),
                "rows": int(len(frame)),
                "valid_adjusted_close": int(frame["adjusted_close"].notna().sum()),
                "start": series.index.min().date().isoformat(),
                "end": series.index.max().date().isoformat(),
                "redistribution": "raw data not committed; runtime access only",
            }
        )
    duplicate_frame = pd.DataFrame(
        duplicate_rows, columns=["source", "symbol", "duplicates"]
    )
    return DownloadedMarketData(daily=daily, manifest=records, duplicates=duplicate_frame)
