"""CSV and opt-in NSTA cache workflows; outputs stay under the configured root."""

from __future__ import annotations

import hashlib
import io
import json
import math
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter
from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader
from worldenergydata.ukcs.production.nsta_client import NSTAClient
from worldenergydata.ukcs.reference_chain import run_ukcs_reference_chain
from worldenergydata.ukcs.report import build_report_facts, render_report_html


class _FrameLoader:
    def __init__(self, normalized):
        self.frame = normalized

    def load_all_production(self):
        return self.frame.copy()

    def load_field_production(self, field_name):
        return self.frame[self.frame.field == field_name.upper().strip()].copy()


def _positive_integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _live_frame(data, input_root):
    if not isinstance(data.get("cache_dir"), str) or not data["cache_dir"].strip():
        raise ValueError("nsta_live requires an explicit cache_dir")
    years = data.get("year")
    years = years if isinstance(years, list) else [years]
    for year in years:
        _positive_integer(year, "year")
    if not years or len(set(years)) != len(years):
        raise ValueError("year list must be nonempty and unique")
    limit = _positive_integer(data.get("max_records"), "max_records")
    refresh = data.get("force_refresh", False)
    if not isinstance(refresh, bool):
        raise TypeError("force_refresh must be a boolean")
    client = NSTAClient(cache_dir=str(input_root / data["cache_dir"]))
    frames, caches = [], []
    combined_digest = hashlib.sha256()
    for year in years:
        client.download(year, force_refresh=refresh, max_records=limit)
        cache = client.cache_dir / f"nsta_production_{year}_monthly.csv"
        if not cache.is_file():
            raise ValueError("NSTA download did not produce a verifiable cache file")
        with cache.open("rb") as stream:
            before = os.fstat(stream.fileno())
            payload = stream.read()
            after = os.fstat(stream.fileno())
        if (before.st_mtime_ns, before.st_size) != (after.st_mtime_ns, after.st_size):
            raise ValueError("NSTA cache changed during readback")
        digest = hashlib.sha256(payload).hexdigest()
        snapshots = client.cache_dir / "snapshots"
        snapshots.mkdir(exist_ok=True)
        snapshot = snapshots / f"{digest}.csv"
        if snapshot.exists():
            if hashlib.sha256(snapshot.read_bytes()).hexdigest() != digest:
                raise ValueError("Retained NSTA snapshot digest mismatch")
        else:
            snapshot.write_bytes(payload)
        combined_digest.update(payload)
        # Parse the exact digested bytes, even if the mutable cache is replaced.
        frame = pd.read_csv(io.BytesIO(payload), encoding="utf-8")
        if not frame.empty and set(frame.PERIODYR.astype(int)) != {year}:
            raise ValueError("NSTA cache year does not match the requested year")
        stamp = datetime.fromtimestamp(before.st_mtime, timezone.utc).isoformat()
        caches.append(
            {
                "year": year,
                "sha256": digest,
                "refreshed_at": stamp,
                "cached_row_count": len(frame),
            }
        )
        frames.append(frame.head(limit))
    evidence = {
        "cache_verified": True,
        "sha256": combined_digest.hexdigest(),
        "caches": caches,
        "requested_years": years,
        "max_records_per_year": limit,
        "coverage_status": "bounded_extract_not_complete",
    }
    # Oldest constituent cache is the freshness bound for a multi-year report.
    return (
        pd.concat(frames, ignore_index=True),
        evidence,
        min(c["refreshed_at"] for c in caches),
    )


def _normalize(raw):
    required = [
        "FIELDNAME",
        "PERIODYR",
        "PERIODMNTH",
        "OILPRODMAS",
        "AGASPROKSM",
        "DGASPROKSM",
        "WATPRODVOL",
    ]
    if missing := sorted(set(required) - set(raw.columns)):
        raise ValueError(f"Missing NSTA columns: {', '.join(missing)}")
    if (
        raw.empty
        or raw.FIELDNAME.isna().any()
        or raw.FIELDNAME.astype(str).str.strip().eq("").any()
    ):
        raise ValueError("No production records or missing field names")
    raw = raw.copy()
    for name in required[1:]:
        raw[name] = pd.to_numeric(raw[name], errors="raise")
        if not raw[name].map(lambda v: math.isfinite(v) and v >= 0).all():
            raise ValueError(
                f"{name} requires finite nonnegative values; missing data are not zeros"
            )
    for name in ("PERIODYR", "PERIODMNTH"):
        if not raw[name].eq(raw[name].astype(int)).all():
            raise ValueError(f"{name} must contain integer periods")
    if not raw.PERIODMNTH.between(1, 12).all():
        raise ValueError("month must be a calendar month")
    return UKCSFieldProductionLoader().load(raw)


def _validate_periods(report):
    periods = {}
    for key in ("start", "end"):
        value = report.get(key)
        if value is None:
            continue
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
            raise ValueError("Report period boundaries must use YYYY-MM")
        try:
            periods[key] = datetime.strptime(value, "%Y-%m")
        except ValueError as error:
            raise ValueError(
                "Report period boundary is not a valid calendar month"
            ) from error
    if len(periods) == 2 and periods["start"] > periods["end"]:
        raise ValueError("Report period start must not follow end")


class Ukcs:
    """Run the existing chain without implicit synthetic fallback or fiscal claims."""

    def run(self, cfg):
        data, report = cfg.get("data", {}), cfg.get("report", {})
        price = report.get("oil_price_usd_bbl")
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price < 0
        ):
            raise ValueError(
                "report.oil_price_usd_bbl must be an explicit finite nonnegative input"
            )
        _validate_periods(report)
        input_root = Path(cfg["Analysis"]["analysis_root_folder"])
        source = data.get("source")
        if source == "csv":
            path = input_root / data["input_path"]
            payload = path.read_bytes()
            raw = pd.read_csv(io.BytesIO(payload), encoding="utf-8")
            evidence = {
                "sha256": hashlib.sha256(payload).hexdigest(),
                "cache_verified": False,
                "coverage_status": "synthetic_fixture",
            }
            stamp = None
        elif source == "nsta_live":
            raw, evidence, stamp = _live_frame(data, input_root)
        else:
            raise ValueError("data.source must be csv or nsta_live")
        normalized = _normalize(raw)
        field_name = report.get("field_name")
        if not isinstance(field_name, str) or not field_name.strip():
            raise ValueError("report.field_name must explicitly select a field")
        meta = dict(report.get("field_meta", {}))
        if (
            str(meta.get("field_name", field_name)).casefold().strip()
            != field_name.casefold().strip()
        ):
            raise ValueError("field_meta.field_name must match the selected field")
        meta["field_name"] = field_name
        if (
            meta.get("water_depth_m") is None
            or isinstance(meta["water_depth_m"], bool)
            or not isinstance(meta["water_depth_m"], (int, float))
            or not math.isfinite(meta["water_depth_m"])
            or meta["water_depth_m"] < 0
        ):
            raise ValueError(
                "water_depth_m must be explicitly supplied, finite and nonnegative"
            )
        adapter = UkcsAdapter(loader=_FrameLoader(normalized))
        from worldenergydata.production.unified.query import ProductionQuery

        query = ProductionQuery(
            regions=["ukcs"],
            fields=[field_name],
            start=report.get("start"),
            end=report.get("end"),
        )
        selected = adapter.fetch(query)
        if selected.empty:
            raise ValueError(
                "No production records match the selected field and period"
            )
        monthly = normalized.groupby(["field", "year", "month"], as_index=False)[
            ["oil_bbl", "gas_mcf", "water_bbl"]
        ].sum(min_count=1)
        result = run_ukcs_reference_chain(
            adapter=UkcsAdapter(loader=_FrameLoader(monthly)),
            field_meta=meta,
            field_name=field_name,
            start=report.get("start"),
            end=report.get("end"),
            oil_price_usd_bbl=price,
        )
        # Report coverage retains reporting-unit rows; cashflow uses monthly sums.
        result["unified_production"] = selected
        evidence["source_row_count"] = len(raw)
        evidence["source_field_count"] = int(normalized.field.nunique())
        return build_report_facts(
            result,
            provenance=source,
            refreshed_at=stamp,
            input_echo=report,
            source_evidence=evidence,
        )

    def router(self, cfg):
        label = cfg.get("meta", {}).get("label", "ukcs_reference_report")
        if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", label):
            raise ValueError("meta.label must be a simple filename label")
        facts = self.run(cfg)
        folder = Path(cfg["Analysis"]["result_folder"])
        folder.mkdir(parents=True, exist_ok=True)
        html_path = folder / f"{label}_report.html"
        json_path = folder / f"{label}_facts.json"
        html_path.write_text(render_report_html(facts), encoding="utf-8", newline="\n")
        json_path.write_text(
            json.dumps(facts, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        cfg["ukcs"] = {
            "status": "completed",
            "outputs": {
                "report_html": html_path.as_posix(),
                "facts_json": json_path.as_posix(),
            },
        }
        return cfg
