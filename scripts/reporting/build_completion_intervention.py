"""Build completion/intervention characterisation from pinned public archives.

Download the URLs recorded in the criteria to a source directory, retaining
their exact bytes. The existing BSEE ZIP processor performs the parsing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from worldenergydata.bsee.analysis.completion_intervention.activity import (
    Parameters,
    analyse,
    read_archive,
)
from worldenergydata.bsee.analysis.completion_intervention.report import (
    digest,
    json_bytes,
    validate_run_record,
    write_products,
)

CRITERIA = Path("config/analysis/bsee/completion_intervention.json")
OUTPUT = Path("docs/modules/bsee/analysis/completion_intervention")
CODE = Path(
    "packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/completion_intervention"
)


def load_source(spec, directory):
    name = spec["file"]
    if Path(name).name != name:
        raise ValueError("source file must be a single filename")
    path = Path(directory) / name
    if digest(path) != spec["sha256"]:
        raise ValueError(f"import digest mismatch: {name}")
    return read_archive(path, spec["members"])


def _member_digest(archive, member):
    matches = [n for n in archive.namelist() if Path(n).name == member + ".txt"]
    if len(matches) != 1:
        raise ValueError("source member is missing or ambiguous")
    value = hashlib.sha256()
    with archive.open(matches[0]) as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def _years(frame):
    preference = [
        "COMPLETION_DATE",
        "WAR_START_DT",
        "BOREHOLE_STAT_DT",
        "WELL_ACTV_START_DT",
        "WELL_SPUD_DATE",
    ]
    column = next((c for c in preference if c in frame), None)
    if column is None:
        return "not supplied", None
    dates = pd.to_datetime(
        frame[column], format="mixed", dayfirst=False, errors="coerce"
    )
    years = sorted(set(int(x) for x in dates.dt.year.dropna()))
    return ", ".join(str(x) for x in years) if years else "not established", column


def _catalogue_source(spec, tables, sources):
    rows = []
    with zipfile.ZipFile(Path(sources) / spec["file"]) as archive:
        for member, frame in tables.items():
            years, year_basis = _years(frame)
            rows.append(
                {
                    "source_id": "bsee-data-center",
                    "publisher_name": spec["publisher_name"],
                    "member": member,
                    "url": spec["url"],
                    "retrieved_at": spec["retrieved_at"],
                    "http_status": spec["http_status"],
                    "status": "used",
                    "readiness": "partial: record characterisation only",
                    "sha256": spec["sha256"],
                    "member_sha256": _member_digest(archive, member),
                    "record_count": len(frame),
                    "fields": list(frame.columns),
                    "years": years,
                    "year_basis": year_basis,
                    "reason": "Archive digest checked before parsing; years follow the stated source date column, where supplied.",
                }
            )
    return rows


def _held_samples():
    root = Path("data/modules/bsee/current")
    files = [
        "completions/completion_summary.csv",
        "completions/completion_properties.csv",
        "completions/completion_perforations.csv",
        "operations/well_activity_summary.csv",
        "operations/well_activity_remarks.csv",
        "wells/well_data.csv",
    ]
    result = []
    for name in files:
        path = root / name
        if not path.exists():
            continue
        frame = pd.read_csv(path, dtype=str)
        years, basis = _years(frame)
        result.append(
            {
                "source_id": "bsee-data-center",
                "publisher_name": "Repository-held BSEE snapshot",
                "member": path.as_posix(),
                "url": "https://www.data.bsee.gov/Main/RawData.aspx",
                "retrieved_at": "not recorded",
                "status": "held, not used",
                "sha256": digest(path),
                "member_sha256": None,
                "record_count": len(frame),
                "fields": list(frame.columns),
                "years": years,
                "year_basis": basis,
                "reason": "Original retrieval date and source-member lineage are not established. The repository README documents sample subsets; the directly retrieved pinned archives supply the analysis instead.",
            }
        )
    return result


def _run_record(path, criteria_path):
    criteria_digest = digest(criteria_path)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        record = json.loads(target.read_text())
    else:
        recorded = datetime.now(timezone.utc).isoformat()
        record = {
            "criteria_sha256": criteria_digest,
            "criteria_recorded_at": recorded,
            "first_run_started_at": datetime.now(timezone.utc).isoformat(),
        }
        target.write_bytes(json_bytes(record))
        with target.with_suffix(".log").open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, sort_keys=True) + "\n")
    validate_run_record(record, criteria_digest)
    return record


def _load_tables(criteria, sources):
    tables, catalogue = {}, []
    for spec in criteria["sources"]:
        parsed = load_source(spec, sources)
        if tables.keys() & parsed.keys():
            raise ValueError("a selected table occurs in more than one source")
        tables.update(parsed)
        catalogue.extend(_catalogue_source(spec, parsed, sources))
    for spec in criteria["unavailable"]:
        catalogue.append(
            {
                **spec,
                "member": spec["file"],
                "record_count": None,
                "years": "not established",
                "fields": [],
                "member_sha256": None,
            }
        )
    return tables, catalogue + _held_samples()


def build(criteria_path, sources, output, run_record):
    criteria = json.loads(Path(criteria_path).read_text())
    record = _run_record(run_record, criteria_path)
    tables, catalogue = _load_tables(criteria, sources)
    result = analyse(tables, Parameters(**criteria["parameters"]))
    result["catalogue"] = catalogue
    result["eor_vocabulary"] = (
        tables["mv_eor_operationcodes"]
        .fillna("")
        .sort_values("VALUE")
        .to_dict("records")
    )
    result["completion_status_vocabulary"] = (
        tables["mv_eor_compstatcodes"]
        .fillna("")
        .sort_values("VALUE")
        .to_dict("records")
    )
    implementation = [
        CODE / "__init__.py",
        CODE / "activity.py",
        CODE / "report.py",
        Path("scripts/reporting/build_completion_intervention.py"),
    ]
    provenance = {
        "run_record": record,
        "criteria_file": Path(criteria_path).as_posix(),
        "source_revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True
        ).strip(),
        "implementation_sha256": {p.as_posix(): digest(p) for p in implementation},
        "criteria_version": criteria["version"],
        "source_id": criteria["source_id"],
        "dataset_owner": criteria["dataset_owner"],
        "intended_use": criteria["intended_use"],
        "rights_basis": criteria["rights_basis"],
        "source_files": [
            {
                "file": x["file"],
                "sha256": x["sha256"],
                "url": x["url"],
                "retrieved_at": x["retrieved_at"],
            }
            for x in criteria["sources"]
        ],
    }
    return write_products(result, criteria["report"], output, provenance)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--criteria", type=Path, default=CRITERIA)
    parser.add_argument("--sources", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--run-record", type=Path, required=True)
    args = parser.parse_args()
    manifest = build(args.criteria, args.sources, args.output, args.run_record)
    print(
        json.dumps(
            {"summary": manifest["summary"], "outputs": manifest["outputs"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
