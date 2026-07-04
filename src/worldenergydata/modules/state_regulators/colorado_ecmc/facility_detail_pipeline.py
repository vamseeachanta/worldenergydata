"""End-to-end Colorado ECMC FacilityDetail/Form 5A ingest runner (#751)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import shapefile
import yaml

from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail import (
    classify_facility_detail_pressures,
    parse_facility_detail_html,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_candidates import (
    build_form5a_pressure_candidates,
    evaluate_screen_promotion,
)
from worldenergydata.modules.state_regulators.colorado_ecmc.facility_detail_ingest import (
    build_facility_detail_source_list,
    fetch_facility_detail_pages,
)


def load_config(config_path: str | Path) -> dict:
    with Path(config_path).open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def read_raw_wells_source(source_config: dict) -> pd.DataFrame:
    """Read the configured WELLS source with raw ECMC DBF field names intact."""
    path = Path(source_config["path"])
    suffix = path.suffix.lower()
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".csv":
        return pd.read_csv(path)
    with _shapefile_reader(path) as reader:
        field_names = [field[0] for field in reader.fields[1:]]
        records = [
            dict(zip(field_names, record, strict=False)) for record in reader.records()
        ]
    return pd.DataFrame.from_records(records)


def parse_facility_detail_pages(fetch_manifest: dict) -> tuple[pd.DataFrame, dict]:
    frames = []
    quality = {
        "fetched_pages": int(len(fetch_manifest.get("fetched", []))),
        "parsed_pages": 0,
        "no_initial_test_pages": 0,
        "parsed_initial_test_rows": 0,
    }
    for metadata in fetch_manifest.get("fetched", []):
        html = Path(metadata["raw_path"]).read_text(encoding="utf-8", errors="ignore")
        parsed = parse_facility_detail_html(html, metadata.get("source_url"))
        if parsed.empty:
            quality["no_initial_test_pages"] += 1
            continue
        parsed = parsed.assign(
            raw_path=metadata.get("raw_path"),
            sha256=metadata.get("sha256"),
            downloaded_at=metadata.get("downloaded_at"),
        )
        frames.append(parsed)
        quality["parsed_pages"] += 1
        quality["parsed_initial_test_rows"] += int(len(parsed))
    if not frames:
        empty = parse_facility_detail_html("", None)
        return empty.assign(raw_path=pd.NA, sha256=pd.NA, downloaded_at=pd.NA), quality
    return pd.concat(frames, ignore_index=True), quality


def run_facility_detail_ingest(config_path: str | Path) -> dict:
    config = load_config(config_path)
    base_dir = Path(config["storage"]["base_dir"])
    wells = read_raw_wells_source(config["source_list"])
    source_list, source_quality = build_facility_detail_source_list(wells, config)
    _write_source_list_outputs(base_dir, source_list, source_quality)
    if config.get("dry_run_source_list_only"):
        summary = _summary(source_quality, {}, {}, {}, {})
        _write_report(base_dir, summary)
        return summary

    fetch_manifest = fetch_facility_detail_pages(source_list, config)
    parsed, parser_quality = parse_facility_detail_pages(fetch_manifest)
    classified = classify_facility_detail_pressures(parsed)
    candidates, candidate_quality = build_form5a_pressure_candidates(classified, config)
    promotion = evaluate_screen_promotion(candidates, candidate_quality, config)
    summary = _summary(
        source_quality, fetch_manifest, parser_quality, candidate_quality, promotion
    )
    _write_outputs(
        base_dir, parsed, parser_quality, candidates, candidate_quality, summary
    )
    return summary


def _write_source_list_outputs(
    base_dir: Path, source_list: pd.DataFrame, source_quality: dict
) -> None:
    out_dir = base_dir / "source_lists"
    out_dir.mkdir(parents=True, exist_ok=True)
    source_list.to_parquet(out_dir / "facility_detail_source_list.parquet")
    (out_dir / "facility_detail_source_list_quality.json").write_text(
        json.dumps(source_quality, indent=2), encoding="utf-8"
    )


def _write_outputs(
    base_dir: Path,
    parsed: pd.DataFrame,
    parser_quality: dict,
    candidates: pd.DataFrame,
    candidate_quality: dict,
    summary: dict,
) -> None:
    parsed_dir = base_dir / "parsed"
    parsed_dir.mkdir(parents=True, exist_ok=True)
    _parquet_safe_frame(parsed).to_parquet(
        parsed_dir / "facility_detail_initial_tests.parquet"
    )
    parsed.to_json(
        parsed_dir / "facility_detail_initial_tests.json",
        orient="records",
        date_format="iso",
        indent=2,
    )
    (parsed_dir / "parser_quality.json").write_text(
        json.dumps(parser_quality, indent=2), encoding="utf-8"
    )
    pressure_dir = base_dir / "curated" / "pressure"
    pressure_dir.mkdir(parents=True, exist_ok=True)
    _parquet_safe_frame(candidates).to_parquet(
        pressure_dir / "well_pressure_observations.parquet"
    )
    (
        pressure_dir / "colorado_ecmc_form5a_pressure_observation_quality.json"
    ).write_text(json.dumps(candidate_quality, indent=2), encoding="utf-8")
    _write_report(base_dir, summary)


def _summary(
    source_quality: dict,
    fetch_manifest: dict,
    parser_quality: dict,
    candidate_quality: dict,
    promotion: dict,
) -> dict:
    return {
        "source_quality": source_quality,
        "fetch_counts": {
            key: len(fetch_manifest.get(key, []))
            for key in ["fetched", "failed", "skipped"]
        },
        "parser_quality": parser_quality,
        "candidate_quality": candidate_quality,
        "promotion": promotion,
        "written_at": datetime.now(timezone.utc).isoformat(),
    }


def _write_report(base_dir: Path, summary: dict) -> None:
    report_dir = base_dir / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "colorado_ecmc_form5a_ingest_summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )


def _parquet_safe_frame(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in result.select_dtypes(include=["object"]).columns:
        result[column] = result[column].map(_nullable_text).astype("string")
    return result


def _nullable_text(value: object) -> str | None:
    if pd.isna(value):
        return None
    return str(value)


def _shapefile_reader(path: Path):
    if path.suffix.lower() != ".zip":
        return shapefile.Reader(str(path))
    with ZipFile(path) as archive:
        return shapefile.Reader(
            shp=archive.open(_zip_member(archive, ".shp")),
            shx=archive.open(_zip_member(archive, ".shx")),
            dbf=archive.open(_zip_member(archive, ".dbf")),
        )


def _zip_member(archive: ZipFile, suffix: str) -> str:
    for name in archive.namelist():
        if name.lower().endswith(suffix):
            return name
    raise ValueError(f"ECMC wells shapefile ZIP missing {suffix} member")


def main() -> None:
    parser = argparse.ArgumentParser(description="Colorado ECMC Form 5A ingest (#751)")
    parser.add_argument(
        "--config", default="config/colorado_ecmc_facility_detail_ingest.yml"
    )
    args = parser.parse_args()
    print(json.dumps(run_facility_detail_ingest(args.config), indent=2))


if __name__ == "__main__":
    main()
