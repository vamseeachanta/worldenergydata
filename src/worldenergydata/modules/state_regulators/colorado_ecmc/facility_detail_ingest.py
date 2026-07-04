"""Production FacilityDetail/Form 5A ingest for Colorado ECMC (#751)."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from time import sleep
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_candidates import (
    build_form5a_pressure_candidates,
    evaluate_screen_promotion,
)

__all__ = [
    "build_facility_detail_source_list",
    "fetch_facility_detail_pages",
    "build_form5a_pressure_candidates",
    "evaluate_screen_promotion",
]

REQUIRED_WELL_COLUMNS = {
    "API",
    "API_County",
    "API_Seq",
    "API_Label",
    "Facil_Id",
    "Field_Name",
    "Max_MD",
    "Max_TVD",
}


def build_facility_detail_source_list(
    wells: pd.DataFrame, config: dict
) -> tuple[pd.DataFrame, dict]:
    """Build FacilityDetail request rows from raw ECMC WELLS data."""
    _validate_columns(wells, REQUIRED_WELL_COLUMNS, "raw ECMC WELLS")
    rows = []
    for _, row in wells.iterrows():
        api_fragment = _api_fragment(row)
        _validate_api_label(api_fragment, row["API_Label"])
        rows.append(
            {
                "api_fragment": api_fragment,
                "api10": f"05{api_fragment}",
                "api12": pd.NA,
                "facility_id": _text(row["Facil_Id"]),
                "field": _text(row["Field_Name"]),
                "max_md_ft": pd.to_numeric(row["Max_MD"], errors="coerce"),
                "max_tvd_ft": pd.to_numeric(row["Max_TVD"], errors="coerce"),
                "latitude": pd.to_numeric(row.get("Latitude"), errors="coerce"),
                "longitude": pd.to_numeric(row.get("Longitude"), errors="coerce"),
            }
        )
    source_list = pd.DataFrame(rows).drop_duplicates("api_fragment")
    max_requests = int(config.get("max_requests", len(source_list)))
    if max_requests >= len(source_list) and not config.get("allow_full_source_list"):
        raise ValueError(
            "full source list run requires allow_full_source_list approval"
        )
    source_list = source_list.head(max_requests)
    quality = {
        "source_rows": int(len(wells)),
        "request_rows": int(len(source_list)),
        "max_requests": max_requests,
        "allow_full_source_list": bool(config.get("allow_full_source_list")),
    }
    return source_list.reset_index(drop=True), quality


def fetch_facility_detail_pages(source_list: pd.DataFrame, config: dict) -> dict:
    """Fetch approved FacilityDetail pages with resumable provenance."""
    base = Path(config["storage"]["base_dir"])
    raw_dir = base / "raw" / "facility_detail" / "html"
    status_dir = base / "raw" / "facility_detail" / "status"
    raw_dir.mkdir(parents=True, exist_ok=True)
    status_dir.mkdir(parents=True, exist_ok=True)
    fetched, failed = [], []
    settings = config["facility_detail"]
    for index, row in source_list.reset_index(drop=True).iterrows():
        try:
            metadata = _fetch_one_page(row, raw_dir, settings)
        except HTTPError as error:
            metadata = _failed_metadata(row, settings, error)
            failed.append(metadata)
            _append_jsonl(status_dir / "failed.jsonl", metadata)
        else:
            if _should_exclude_identity_mismatch(metadata, settings):
                metadata = _identity_mismatch_metadata(metadata)
                failed.append(metadata)
                _append_jsonl(status_dir / "failed.jsonl", metadata)
            else:
                fetched.append(metadata)
                _append_jsonl(status_dir / "fetched.jsonl", metadata)
        if index < len(source_list) - 1:
            sleep(float(settings.get("request_delay_seconds", 0)))
    return {"fetched": fetched, "failed": failed, "skipped": []}


def _fetch_one_page(row: pd.Series, raw_dir: Path, settings: dict) -> dict:
    api_fragment = str(row["api_fragment"])
    url = _facility_detail_url(api_fragment, settings["base_url"])
    request = Request(url, headers={"User-Agent": settings["user_agent"]})
    with urlopen(request, timeout=int(settings.get("timeout_seconds", 60))) as response:
        payload = response.read()
        status_code = response.getcode()
        headers = response.headers
    raw_path = raw_dir / f"{api_fragment}.html"
    raw_path.write_bytes(payload)
    text = payload.decode("utf-8", errors="ignore")
    return {
        "api_fragment": api_fragment,
        "facility_id": _text(row.get("facility_id")),
        "rendered_api_fragment": _rendered_api_fragment(text),
        "rendered_facility_id": _rendered_facility_id(text),
        "source_url": url,
        "raw_path": str(raw_path),
        "status_code": int(status_code),
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "etag": headers.get("ETag"),
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "retry_count": 0,
    }


def _facility_detail_url(api_fragment: str, base_url: str) -> str:
    return f"{base_url}?{urlencode({'api': api_fragment})}"


def _failed_metadata(row: pd.Series, settings: dict, error: HTTPError) -> dict:
    api_fragment = str(row["api_fragment"])
    status_code = int(error.code)
    return {
        "api_fragment": api_fragment,
        "facility_id": _text(row.get("facility_id")),
        "source_url": _facility_detail_url(api_fragment, settings["base_url"]),
        "status_code": status_code,
        "error_class": error.__class__.__name__,
        "error_text": str(error),
        "retryable": status_code not in {403, 404},
        "retry_count": 0,
        "failed_at": datetime.now(timezone.utc).isoformat(),
    }


def _should_exclude_identity_mismatch(metadata: dict, settings: dict) -> bool:
    return bool(settings.get("stop_on_identity_mismatch")) and _has_identity_mismatch(
        metadata
    )


def _has_identity_mismatch(metadata: dict) -> bool:
    rendered_api = metadata.get("rendered_api_fragment")
    if rendered_api and rendered_api != metadata["api_fragment"]:
        return True
    rendered_facility = metadata.get("rendered_facility_id")
    facility_id = metadata.get("facility_id")
    return bool(rendered_facility and facility_id and rendered_facility != facility_id)


def _identity_mismatch_metadata(metadata: dict) -> dict:
    failed = dict(metadata)
    failed.update(
        {
            "status": "identity_mismatch",
            "error_class": "IdentityMismatch",
            "error_text": (
                "rendered FacilityDetail identity does not match requested API/facility"
            ),
            "retryable": False,
            "failed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    return failed


def _append_jsonl(path: Path, row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _validate_columns(frame: pd.DataFrame, required: set[str], label: str) -> None:
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"{label} missing required columns: {', '.join(missing)}")


def _api_fragment(row: pd.Series) -> str:
    api = _digits(row.get("API"))
    if len(api) == 8:
        return api
    county = _digits(row.get("API_County")).zfill(3)
    sequence = _digits(row.get("API_Seq")).zfill(5)
    fragment = f"{county}{sequence}"
    if not re.fullmatch(r"\d{8}", fragment):
        raise ValueError("raw ECMC WELLS row has invalid API fragment")
    return fragment


def _validate_api_label(api_fragment: str, label: object) -> None:
    digits = _digits(label)
    expected = f"05{api_fragment}"
    if digits != expected:
        raise ValueError(f"API_Label {label!r} does not match {expected}")


def _digits(value: object) -> str:
    if pd.isna(value):
        return ""
    return "".join(char for char in str(value) if char.isdigit())


def _rendered_api_fragment(text: str) -> str:
    match = re.search(r"API\s*#?\s*[:#]?\s*(05[-\s]?\d{3}[-\s]?\d{5})", text, re.I)
    if not match:
        return ""
    digits = _digits(match.group(1))
    return digits[2:] if len(digits) == 10 and digits.startswith("05") else ""


def _rendered_facility_id(text: str) -> str:
    match = re.search(r"Facility\s*ID\s*[:#]?\s*(\d+)", text, re.I)
    return match.group(1) if match else ""


def _text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()
