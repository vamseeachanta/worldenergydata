"""Produce the part 2 r15 CSVs from locally retained BSEE archives."""

import argparse
import hashlib
import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent))

from issue2_public_data_r9 import build_r9 as r9
from issue2_public_data_r12 import build_r12 as r12
from issue2_public_data_r12 import derive_r12
from issue2_public_data_r15.compare_r15 import compare_tables
from issue2_public_data_r15.permits import permit_tables
from rawdata_fact_check import count_rawdata

APD = "APDRawData.zip"
APM = "eWellAPMRawData.zip"
BORE = "BoreholeRawData.zip"


def verify_digest(path, expected):
    """Return the exact bytes that matched the pin, including for symlink inputs."""
    content = path.read_bytes()
    actual = hashlib.sha256(content).hexdigest()
    if actual != expected:
        raise ValueError(f"{path.name}: expected SHA-256 {expected}, actual {actual}")
    return content


def stage_inputs(data_dir, staged):
    receipts = json.loads((ROOT / "source-pins.json").read_text(encoding="utf-8"))
    if sorted(r["file"] for r in receipts) != sorted([APD, APM, BORE, derive_r12.WTI.name]):
        raise ValueError("Expected one source receipt per BSEE archive and one for WTI")
    for receipt in receipts:
        name = receipt["file"]
        path = derive_r12.WTI if name == derive_r12.WTI.name else data_dir / name
        (staged / name).write_bytes(verify_digest(path, receipt["sha256"]))
    return pd.DataFrame(receipts)


def permit_data(data_dir, headers):
    # Both APD members were checked for duration fields in the r12 appendix.
    def read_member(member):
        rows = count_rawdata.read_member(data_dir / APD, member + ".txt")
        for column in rows[0]:
            if "DAY" in column or "DUR" in column:
                raise ValueError(f"APD duration schema changed: {member}/{column}")
            headers.append(dict(file=APD, member=member, column=column))
        return rows

    read_member("mv_apddata_all")
    rows = read_member("mv_apd_main_all")
    tables, excluded = permit_tables(rows)
    kept = int(tables["fig-p1-new-well-permits-by-rig-type"].total.sum())
    return tables, partition("APD", len(rows), "first_permit_in_period", kept, excluded)


def map_data(bore, wti_path):
    legacy, audit = r9.map_wells(bore)
    # wells_by_year sets MAP_PERIODS on its module. Use the r12 private r9 instance.
    wells, annual_audit = derive_r12.wells_by_year(derive_r12.load_r9(), bore)
    if annual_audit.missing_or_outside_coordinates.any():
        raise ValueError("Selected borehole outside the map or missing coordinates")
    counts = derive_r12.yearly_counts(wells, r9.BANDS)
    wti = derive_r12.wti_annual(wti_path)
    return {
        "map-wells": legacy, "map-selection": audit, "map-summary": r9.map_summary(legacy).reset_index(),
        "map-wells-by-year": wells, "new-wells-by-year": counts,
        "map-windows": r12.window_counts(counts), "wti-annual": wti,
        "new-wells-trend": r12.trend_table(counts, wti),
    }


def partition(source, raw, kept_reason, kept, excluded):
    if kept + sum(excluded.values()) != raw or any(n < 0 for n in excluded.values()):
        raise ValueError(f"{source}: {raw} input rows, {kept} kept, exclusions {excluded}")
    return [
        dict(source=source, disposition=disposition, reason=reason, records=n)
        for disposition, reason, n in [
            ("read", "main_member_rows", raw), ("kept", kept_reason, kept),
            *(("excluded", reason, n) for reason, n in excluded.items()),
        ]
    ]


def duration_data(data_dir, bore, headers):
    apm, sub, primary, subdefs = [
        r9.read_table(data_dir, APM, name, headers) for name in
        ("mv_apm_main", "mv_apm_suboperations", "mv_apm_primary_op_codes", "mv_apm_suboperation_codes")
    ]
    events, apm_audit = r9.prepare_apm(apm, sub, bore)
    drilling, bore_audit = r9.prepare_boreholes(bore)
    tables = {
        "subtype-activity": events.attrs.pop("subtype_activity"),
        "repeat-key-sensitivity": events.attrs.pop("sensitivity"),
        "code_mapping": r9.mapping_table(primary, subdefs),
        "days-summary": r9.summarize_days(pd.concat([events, drilling], ignore_index=True)),
        "exclusions": pd.DataFrame([
            dict(source=source, rule=rule, records=n)
            for source, audit in [("APM", apm_audit), ("Borehole", bore_audit)] for rule, n in audit.items()
        ]),
    }
    # The r12 exclusions table also contains overlapping diagnostics. Only the
    # sequential selection losses participate in the raw-row partition.
    bore_reasons = ("duplicate_rows", "non_gulf", "non_original", "cancelled", "missing_spud_date", "outside_years")
    records = partition("Borehole", len(bore), "selected_spuds", len(drilling),
                        {k: bore_audit[k] for k in bore_reasons})
    apm_reasons = ("duplicate_rows", "unmatched_or_ambiguous_region", "non_gulf",
                   "missing_status_date", "outside_years")
    excluded = {k: apm_audit[k] for k in apm_reasons}
    excluded.update({k: n for k, n in apm_audit.items() if k.startswith("Excluded: ")})
    days = tables["days-summary"]
    estimated = days[days.activity.ne(r9.RECORDED)]
    excluded.update(missing_invalid_days=int(estimated.missing_invalid_days.sum()),
                    nonpositive_days=int(estimated.nonpositive_days.sum()))
    records += partition("APM", len(apm), "usable_duration_estimates", int(estimated.n.sum()), excluded)
    return tables, records


def build_tables(data_dir, sources):
    headers = []
    tables, records = permit_data(data_dir, headers)
    bore = r9.read_table(data_dir, BORE, "mv_boreholes_all", headers)
    tables.update(map_data(bore, data_dir / derive_r12.WTI.name))
    duration, duration_records = duration_data(data_dir, bore, headers)
    tables.update(duration)
    tables.update({
        "source-members": r9.archive_members(data_dir), "source_columns": pd.DataFrame(headers),
        "sources": sources, "record-counts": pd.DataFrame(records + duration_records),
    })
    return tables


def derive(data_dir, out=ROOT / "data"):
    baseline = r12.ROOT / "data"
    # Finish every calculation and comparison before replacing any article CSV.
    with TemporaryDirectory(prefix=".derive-", dir=out.parent) as scratch:
        staged = Path(scratch)
        sources = stage_inputs(data_dir, staged)
        tables = build_tables(staged, sources)
        expected = {p.stem for p in baseline.glob("*.csv")} | {"record-counts"}
        if set(tables) != expected:
            raise ValueError(f"Table inventory differs from r12: {sorted(set(tables) ^ expected)}")
        # Keep inputs (including wti-monthly.csv) out of the output inventory.
        staged = staged / "tables"
        staged.mkdir()
        for name, frame in tables.items():
            frame.to_csv(staged / (name + ".csv"), index=False, lineterminator="\n", float_format="%.12g")
        comparison = compare_tables(baseline, staged)
        comparison.to_csv(staged / "r12-vs-r15.csv", index=False, lineterminator="\n", float_format="%.12g")
        out.mkdir(exist_ok=True)
        for path in sorted(staged.glob("*.csv")):
            path.replace(out / path.name)
    print(f"{len(tables) + 1} CSVs written to {out}; {len(comparison)} comparisons")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True, help="folder holding the three pinned BSEE ZIP files")
    args = parser.parse_args()
    try:
        derive(args.data_dir)
    except (FileNotFoundError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
