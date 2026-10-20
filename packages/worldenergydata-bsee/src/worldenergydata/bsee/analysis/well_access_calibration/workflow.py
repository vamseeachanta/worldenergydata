"""Durable CSV workflow; BSEE exports remain read-only inputs."""

from __future__ import annotations

import hashlib
from io import BytesIO
from pathlib import Path

import pandas as pd
import yaml

from .core import build_calibration
from .report import render_html


def run_calibration(config):
    """Load normalized exports and a reviewed well-level analog manifest.

    WAR may be prejoined, or `war_properties_csv` may provide WELL_ACTIVITY_CD
    keyed by SN_WAR. Relative paths resolve against the invocation directory.
    No historical bin schema or platform-to-well join is guessed.
    """
    sources = {
        Path(config[f"{key}_csv"]).resolve() for key in ("wells", "war", "production")
    }
    if config.get("war_properties_csv"):
        sources.add(Path(config["war_properties_csv"]).resolve())
    outputs = config.get("outputs", {})
    if set(outputs) - {"calibration_yml", "report_html"}:
        raise ValueError("Unknown calibration output")
    destinations = [Path(value).resolve() for value in outputs.values()]
    if sources.intersection(destinations):
        raise ValueError("Outputs must not overwrite input evidence")
    if len(destinations) != len(set(destinations)):
        raise ValueError("Outputs must use distinct paths")
    frames, digests = {}, {}
    for key in ("wells", "war", "production"):
        path = Path(config[f"{key}_csv"])
        content = path.read_bytes()
        digests[key] = hashlib.sha256(content).hexdigest()
        frames[key] = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
    if config.get("war_properties_csv"):
        path = Path(config["war_properties_csv"])
        content = path.read_bytes()
        prop = pd.read_csv(BytesIO(content), dtype=str, keep_default_na=False)
        digests["war_properties"] = hashlib.sha256(content).hexdigest()
        prop = prop[["SN_WAR", "WELL_ACTIVITY_CD"]].drop_duplicates()
        frames["war"] = frames["war"].merge(
            prop, on="SN_WAR", how="left", validate="many_to_one"
        )
        if frames["war"]["WELL_ACTIVITY_CD"].isna().any():
            raise ValueError("Missing WAR activity properties")
    parameter_keys = (
        "observation_start",
        "observation_end",
        "band_edges_yr",
        "days_per_year",
        "event_gap_days",
        "min_events",
        "min_exposure_years",
        "dry_tree_codes",
        "coverage_basis",
        "analog_basis",
    )
    result = build_calibration(
        **frames, parameters={k: config[k] for k in parameter_keys}
    )
    result["meta"]["input_sha256"] = digests
    result["meta"]["data_basis"] = config.get(
        "data_basis", "User-supplied normalized BSEE exports"
    )
    for kind, output in outputs.items():
        path = Path(output)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            render_html(result)
            if kind == "report_html"
            else yaml.safe_dump(result, sort_keys=True)
        )
        path.write_text(content, encoding="utf-8")
    return result
