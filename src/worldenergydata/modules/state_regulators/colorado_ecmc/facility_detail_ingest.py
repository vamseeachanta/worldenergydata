"""Production FacilityDetail/Form 5A ingest for Colorado ECMC (#751)."""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode

import pandas as pd
from bs4 import BeautifulSoup

from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_candidates import (
    build_form5a_pressure_candidates,
    evaluate_screen_promotion,
)
from worldenergydata.modules.state_regulators.fetch import (
    FetchConfig,
    Fetcher,
    TermsCheck,
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
                "source_api": _text(row.get("API")),
                "wellbore_selection": "NOT_EVALUATED",
                "facility_id": _text(row["Facil_Id"]),
                "field": _text(row["Field_Name"]),
                "max_md_ft": pd.to_numeric(row["Max_MD"], errors="coerce"),
                "max_tvd_ft": pd.to_numeric(row["Max_TVD"], errors="coerce"),
                "latitude": pd.to_numeric(row.get("Latitude"), errors="coerce"),
                "longitude": pd.to_numeric(row.get("Longitude"), errors="coerce"),
            }
        )
    source_list = pd.DataFrame(rows).drop_duplicates()
    if source_list.duplicated("api_fragment").any():
        raise ValueError("ambiguous FacilityDetail rows share an API fragment")
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


def fetch_facility_detail_pages(
    source_list: pd.DataFrame, config: dict, *, clock=time.time, sleep=time.sleep
) -> dict:
    """Fetch approved FacilityDetail pages with resumable provenance."""
    base = Path(config["storage"]["base_dir"])
    raw_dir = base / "raw" / "facility_detail" / "html"
    status_dir = base / "raw" / "facility_detail" / "status"
    raw_dir.mkdir(parents=True, exist_ok=True)
    status_dir.mkdir(parents=True, exist_ok=True)
    fetched, failed = [], []
    settings = config["facility_detail"]
    # Shared policy.py FetchConfig is the source of pacing/budget defaults.
    options = dict(settings.get("fetch", {}))
    if "request_delay_seconds" in settings:
        options["fallback_interval"] = float(settings["request_delay_seconds"])
    if "timeout_seconds" in settings:
        options["timeout"] = float(settings["timeout_seconds"])
    if "max_retries" in settings:
        options["max_retries"] = int(settings["max_retries"])
    fetcher = Fetcher(
        FetchConfig(
            base / "raw" / "facility_detail" / "cache",
            settings["user_agent"],
            **options,
        ),
        [TermsCheck(**check) for check in settings.get("terms_checks", [])],
        clock=clock,
        sleep=sleep,
    )
    for _, row in source_list.reset_index(drop=True).iterrows():
        try:
            metadata = _fetch_one_page(row, raw_dir, settings, fetcher)
        except HTTPError as error:
            metadata = _failed_metadata(row, settings, error)
            failed.append(metadata)
            _append_jsonl(status_dir / "failed.jsonl", metadata)
        else:
            metadata["identity_status"] = _identity_status(metadata)
            if _should_exclude_identity_mismatch(metadata, settings):
                metadata = _identity_mismatch_metadata(metadata)
                failed.append(metadata)
                _append_jsonl(status_dir / "failed.jsonl", metadata)
            else:
                fetched.append(metadata)
                _append_jsonl(status_dir / "fetched.jsonl", metadata)
    return {"fetched": fetched, "failed": failed, "skipped": []}


def _fetch_one_page(
    row: pd.Series, raw_dir: Path, settings: dict, fetcher: Fetcher
) -> dict:
    api_fragment = str(row["api_fragment"])
    url = _facility_detail_url(api_fragment, settings["base_url"])
    result = fetcher.fetch(url)
    payload = result.path.read_bytes()
    status_code = result.metadata.get("status_code", 200)
    headers = result.metadata["response_headers"]
    text = BeautifulSoup(payload.decode("utf-8"), "html.parser").get_text(
        " ", strip=True
    )
    raw_path = raw_dir / f"{api_fragment}.html"
    raw_path.write_bytes(payload)
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
        "retry_count": result.metadata.get("retry_count", 0),
        "cached": result.cached,
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
    return (
        _identity_status(metadata) != "matched"
        and settings.get("keep_identity_mismatch") is not True
    )


def _identity_status(metadata: dict) -> str:
    if _has_identity_mismatch(metadata):
        return "identity_mismatch"
    if not metadata.get("rendered_api_fragment"):
        return "identity_unverified"
    return "matched"


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
            "status": metadata["identity_status"],
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
