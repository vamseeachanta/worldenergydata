"""Capped official-source scout for Colorado ECMC FacilityDetail pages (#749)."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd
import yaml

from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail import (
    classify_facility_detail_pressures,
    parse_facility_detail_html,
)

BASE_URL = "https://ecmc.state.co.us/cogisdb/Facility/FacilityDetail.aspx"


def load_source_discovery_config(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        config = yaml.safe_load(handle)
    scout = config["facility_detail"]
    if int(scout["max_requests"]) > len(scout["sample_apis"]):
        raise ValueError("ECMC source discovery max_requests exceeds sample_apis")
    return config


def build_facility_detail_url(api_fragment: str, base_url: str = BASE_URL) -> str:
    digits = "".join(char for char in str(api_fragment) if char.isdigit())
    if len(digits) == 12 and digits.startswith("05"):
        digits = digits[2:10]
    elif len(digits) == 10 and digits.startswith("05"):
        digits = digits[2:10]
    if len(digits) != 8:
        raise ValueError(f"expected Colorado county+sequence API fragment: {api_fragment}")
    return f"{base_url}?{urlencode({'api': digits})}"


def fetch_facility_detail(
    url: str, destination: str | Path, timeout: int = 60
) -> dict:
    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256()
    size = 0
    with urlopen(url, timeout=timeout) as response, path.open("wb") as handle:
        while True:
            chunk = response.read(1 << 20)
            if not chunk:
                break
            handle.write(chunk)
            digest.update(chunk)
            size += len(chunk)
        headers = response.headers
        return {
            "source_url": url,
            "raw_path": str(path),
            "status_code": response.getcode(),
            "size_bytes": size,
            "sha256": digest.hexdigest(),
            "last_modified": headers.get("Last-Modified"),
            "etag": headers.get("ETag"),
            "downloaded_at": datetime.now(timezone.utc).isoformat(),
        }


def write_source_discovery_manifest(
    base_dir: str | Path, downloads: list[dict]
) -> dict:
    base = Path(base_dir)
    manifest_path = base / "raw" / "facility_detail" / "manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source": "colorado_ecmc_facility_detail",
        "request_count": len(downloads),
        "parsed_row_count": int(sum(item.get("parsed_row_count", 0) for item in downloads)),
        "candidate_pressure_count": int(
            sum(item.get("candidate_pressure_count", 0) for item in downloads)
        ),
        "manifest_written_at": datetime.now(timezone.utc).isoformat(),
        "downloads": downloads,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def run_source_discovery(config_path: str | Path) -> dict:
    config = load_source_discovery_config(config_path)
    base_dir = Path(config["storage"]["base_dir"])
    scout = config["facility_detail"]
    raw_dir = base_dir / "raw" / "facility_detail"
    raw_dir.mkdir(parents=True, exist_ok=True)
    downloads, frames = [], []
    for index, api_fragment in enumerate(scout["sample_apis"][: scout["max_requests"]]):
        url = build_facility_detail_url(api_fragment, scout["base_url"])
        raw_path = raw_dir / f"{_api_fragment(api_fragment)}.html"
        metadata = fetch_facility_detail(url, raw_path, scout.get("timeout_seconds", 60))
        parsed = parse_facility_detail_html(raw_path.read_text(encoding="utf-8"), url)
        classified = classify_facility_detail_pressures(parsed)
        metadata["api_fragment"] = _api_fragment(api_fragment)
        metadata["parsed_row_count"] = int(len(classified))
        metadata["candidate_pressure_count"] = int(
            classified["pressure_role"].eq("candidate_pressure_observation").sum()
        )
        downloads.append(metadata)
        frames.append(classified)
        if index < int(scout["max_requests"]) - 1:
            sleep(float(scout["request_delay_seconds"]))
    parsed_frame = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    manifest = write_source_discovery_manifest(base_dir, downloads)
    report = _write_outputs(base_dir, parsed_frame, manifest)
    return {"manifest": manifest, "report": report, "parsed": parsed_frame}


def _write_outputs(base_dir: Path, parsed: pd.DataFrame, manifest: dict) -> dict:
    parsed_dir = base_dir / "parsed"
    report_dir = base_dir / "reports"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    parsed.to_parquet(parsed_dir / "facility_detail_initial_tests.parquet")
    parsed_json = parsed.to_json(orient="records", date_format="iso")
    (parsed_dir / "facility_detail_initial_tests.json").write_text(
        parsed_json, encoding="utf-8"
    )
    report = {
        "source": manifest["source"],
        "request_count": manifest["request_count"],
        "parsed_row_count": manifest["parsed_row_count"],
        "candidate_pressure_count": manifest["candidate_pressure_count"],
        "decision": "facility_detail_candidate_for_follow_up",
        "automated_ingest_follow_up_recommended": True,
        "screen_exclusion": "source_discovery_not_screen_ready",
        "excluded_pressure_lanes": [
            "formation_treatment_pressure",
            "mechanical_integrity_pressure",
            "form_17_bradenhead_pressure",
        ],
        "report_written_at": datetime.now(timezone.utc).isoformat(),
    }
    (report_dir / "colorado_ecmc_pressure_source_discovery.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def _api_fragment(value: str) -> str:
    return build_facility_detail_url(value).rsplit("=", 1)[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Colorado ECMC source scout (#749)")
    parser.add_argument("--config", default="config/colorado_ecmc_source_discovery.yml")
    args = parser.parse_args()
    result = run_source_discovery(args.config)
    print(json.dumps(result["report"], indent=2))


if __name__ == "__main__":
    main()
