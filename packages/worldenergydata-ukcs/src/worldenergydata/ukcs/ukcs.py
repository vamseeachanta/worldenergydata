"""UKCS report workflow: offline CSV by default, explicit live NSTA opt-in."""

from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from worldenergydata.production.unified.adapters.ukcs_adapter import UkcsAdapter
from worldenergydata.ukcs.production.field_production import UKCSFieldProductionLoader
from worldenergydata.ukcs.production.nsta_client import DEFAULT_BASE_URL, NSTAClient
from worldenergydata.ukcs.reference_chain import run_ukcs_reference_chain
from worldenergydata.ukcs.report import build_report_facts, render_report_html


class _NstaFrameLoader:
    def __init__(self, raw):
        self.normalized = UKCSFieldProductionLoader().load(raw)

    def load_field_production(self, field_name):
        return self.normalized[
            self.normalized["field"] == field_name.upper().strip()
        ].copy()

    def load_all_production(self):
        return self.normalized.copy()


def _within_root(root, value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} requires an explicit path")
    path = (root / value).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"{name} must stay under the analysis input root")
    return path


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class Ukcs:
    """Route UKCS chain execution and write only to configured result locations."""

    def router(self, cfg):
        analysis = cfg.get("Analysis", {})
        if not analysis.get("analysis_root_folder") or not analysis.get(
            "result_folder"
        ):
            raise ValueError("Analysis input root and result folder are required")
        facts = self.build_facts(cfg, input_root=Path(analysis["analysis_root_folder"]))
        output = Path(analysis["result_folder"])
        label = cfg.get("meta", {}).get("label", "ukcs_reference_report")
        output.mkdir(parents=True, exist_ok=True)
        report_path = output / f"{label}_report.html"
        facts_path = output / f"{label}_facts.json"
        report_path.write_text(render_report_html(facts), encoding="utf-8")
        facts_path.write_text(
            json.dumps(facts, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        cfg["ukcs"] = {
            "status": "completed",
            "report_html": str(report_path),
            "facts_json": str(facts_path),
        }
        return cfg

    def build_facts(self, cfg, *, input_root):
        """Run the existing chain with source evidence; do not write report files."""
        self._validate(cfg)
        data, report = cfg["data"], cfg["report"]
        root = Path(input_root).resolve()
        if data["source"] == "csv":
            path = _within_root(root, data.get("input_path"), "input_path")
            raw = pd.read_csv(path)
            provenance, refreshed_at = "fixture", None
            evidence = {"raw_sha256": {path.name: _digest(path)}}
        else:
            raw, refreshed_at, evidence = self._live_data(data, root)
            provenance = "nsta_live"
        chain = run_ukcs_reference_chain(
            adapter=UkcsAdapter(loader=_NstaFrameLoader(raw)),
            field_meta=report["field_meta"],
            field_name=report["field_name"],
            start=report.get("start"),
            end=report.get("end"),
            oil_price_usd_bbl=float(report.get("oil_price_usd_bbl", 75.0)),
        )
        if chain["unified_production"].empty:
            raise ValueError(
                "No production observations for the selected field and period"
            )
        facts = build_report_facts(
            chain,
            provenance=provenance,
            source_url=DEFAULT_BASE_URL,
            licence="NSTA Open User Licence",
            refreshed_at=refreshed_at,
            input_echo=report,
        )
        facts["source"].update(evidence)
        return facts

    @staticmethod
    def _live_data(data, root):
        cache_dir = _within_root(root, data.get("cache_dir"), "cache_dir")
        years = data.get("year")
        years = years if isinstance(years, list) else [years]
        if not years or any(
            type(y) is not int or not 1900 <= y <= datetime.now(timezone.utc).year
            for y in years
        ):
            raise ValueError("year requires a calendar year or nonempty list of years")
        if len(set(years)) != len(years):
            raise ValueError("year list must not contain duplicate years")
        limit = data.get("max_records")
        if limit is not None and (type(limit) is not int or limit <= 0):
            raise ValueError("max_records must be a positive integer")
        force_refresh = data.get("force_refresh", False)
        if type(force_refresh) is not bool:
            raise ValueError("force_refresh must be a boolean")
        client = NSTAClient(cache_dir=str(cache_dir))
        frames, digests, timestamps = [], {}, {}
        for year in years:
            cache = cache_dir / f"nsta_production_{year}_monthly.csv"
            if not cache.resolve().is_relative_to(root):
                raise ValueError(
                    "NSTA cache file must stay under the analysis input root"
                )
            client.download(
                year, dataset="monthly", force_refresh=force_refresh, max_records=limit
            )
            if not cache.is_file():
                raise ValueError("Live provenance requires a retained NSTA cache file")
            # Read back the retained bytes, rather than trusting an in-memory return.
            raw = pd.read_csv(cache)
            frames.append(raw.head(limit) if limit else raw)
            digests[cache.name] = _digest(cache)
            timestamps[cache.name] = datetime.fromtimestamp(
                cache.stat().st_mtime, timezone.utc
            ).isoformat()
        return (
            pd.concat(frames, ignore_index=True),
            min(timestamps.values()),
            {
                "raw_sha256": digests,
                "cache_refreshed_at": timestamps,
                "max_records_per_year": limit,
                "coverage_note": "Selected-field observations from the requested year(s). "
                "A record cap may omit fields or months; complete UKCS coverage is not established.",
            },
        )

    @staticmethod
    def _validate(cfg):
        if not isinstance(cfg, dict) or cfg.get("basename") != "ukcs":
            raise ValueError("basename must be ukcs")
        data, report = cfg.get("data"), cfg.get("report")
        if not isinstance(data, dict) or data.get("source") not in {"csv", "nsta_live"}:
            raise ValueError("data.source must be csv or nsta_live")
        if (
            not isinstance(report, dict)
            or not str(report.get("field_name", "")).strip()
        ):
            raise ValueError("report.field_name is required")
        field = report["field_name"]
        meta = report.get("field_meta", {})
        if (
            not isinstance(field, str)
            or not isinstance(meta, dict)
            or str(meta.get("field_name", "")).strip().casefold()
            != field.strip().casefold()
        ):
            raise ValueError("field_meta.field_name must match report.field_name")
        price = report.get("oil_price_usd_bbl", 75.0)
        try:
            valid_price = (
                not isinstance(price, bool)
                and math.isfinite(float(price))
                and float(price) >= 0
            )
        except (TypeError, ValueError):
            valid_price = False
        if not valid_price:
            raise ValueError("oil price must be finite and nonnegative")
        label = cfg.get("meta", {}).get("label", "ukcs_reference_report")
        if not isinstance(label, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", label):
            raise ValueError("meta.label must be a filename without path components")
