"""Contractor-only jackup replacement and its public metadata contract."""

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
DATA = ROOT / "data/modules/offshore_assets"
SCRIPT = ROOT / "scripts/field_development/build_contractor_jackups.py"
UNAVAILABLE = {
    "COUNTRY_BUILT",
    "CLASSIFICATION_SOCIETY",
    "MIN_WATER_DEPTH_FT",
    "QUARTERS_CAPACITY",
    "DERRICK_RATING_KIPS",
    "DRAWWORKS_HP",
    "BOP_OPERATING_PRESSURE_KSI",
}


@pytest.fixture
def builder():
    spec = importlib.util.spec_from_file_location("contractor_jackups", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_csv(builder, **changes):
    row = dict.fromkeys(builder.SOURCE_COLUMNS, "")
    row.update(
        rig="Synthetic rig",
        design="Synthetic design",
        year="2016",
        max_water_depth_m="121.9200",
        leg_length_m="157.5816",
        spudcan_diameter_m="13.8074",
        drilling_depth_m="9144.0000",
        hull_length_m="65.2272",
        source_url="https://example.org/spec.pdf;https://example.org/specifications/",
        accessed="2026-10-27",
    )
    row.update(changes)
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=builder.SOURCE_COLUMNS)
    writer.writeheader()
    writer.writerow(row)
    return stream.getvalue().encode("utf-8")


def test_maps_only_contractor_fields_and_converts_metres(builder):
    raw = builder.build_csv(source_csv(builder))
    assert b"\r" not in raw
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    assert len(rows) == 1
    row = rows[0]
    assert list(row) == list(builder.OUTPUT_COLUMNS)
    assert row["RIG_NAME"] == "Synthetic rig"
    assert row["RIG_DESIGN_MODEL"] == "Synthetic design"
    assert row["YEAR_DELIVERED"] == "2016"
    # NIST SP 811 (2008), Appendix B.6, "U.S. survey foot and mile":
    # the international foot gives metres * 1250 / 381, independently by hand.
    # 121.9200 * 1250 = 152400; 152400 / 381 = 400.0.
    assert row["MAX_WATER_DEPTH_RATING_FT"] == "400.0"
    # 157.5816 * 1250 = 196977; 196977 / 381 = 517.0.
    assert row["OVERALL_LEG_LENGTH_FT"] == "517.0"
    # 13.8074 * 1250 = 17259.25, between 381 * 45.25 and 381 * 45.35.
    assert row["SPUD_CAN_DIAMETER_FT"] == "45.3"
    # 9144.0000 * 1250 = 11430000; 11430000 / 381 = 30000.0.
    assert row["MAX_DRILLING_DEPTH_FT"] == "30000.0"
    # 65.2272 * 1250 = 81534; 81534 / 381 = 214.0.
    assert row["OVERALL_HULL_LENGTH_FT"] == "214.0"
    assert all(row[key] == "" for key in UNAVAILABLE)
    assert row["source_url"] == (
        "https://example.org/spec.pdf;https://example.org/specifications/"
    )


def test_missing_particulars_stay_empty(builder):
    raw = source_csv(
        builder,
        design="",
        year="",
        max_water_depth_m="",
        leg_length_m="",
        spudcan_diameter_m="",
        drilling_depth_m="",
        hull_length_m="",
    )
    row = next(csv.DictReader(io.StringIO(builder.build_csv(raw).decode())))
    assert {key for key, value in row.items() if value} == {"RIG_NAME", "source_url"}


@pytest.mark.parametrize(
    "changes",
    [
        {"rig": ""},
        {"source_url": ""},
        {"source_url": "file:spec.pdf"},
        {"accessed": "invalid"},
        {"year": "2016.5"},
        {"max_water_depth_m": "NaN"},
        {"leg_length_m": "-1"},
        {"hull_length_m": "0"},
    ],
)
def test_rejects_invalid_input(builder, changes):
    with pytest.raises(ValueError):
        builder.build_csv(source_csv(builder, **changes))


def test_rejects_duplicate_rigs_and_wrong_source_schema(builder):
    raw = source_csv(builder)
    duplicate = raw + raw.splitlines(keepends=True)[1]
    with pytest.raises(ValueError, match="duplicate"):
        builder.build_csv(duplicate)
    with pytest.raises(ValueError, match="schema"):
        builder.build_csv(b"RIG_NAME,source_url\nSynthetic rig,https://example.org/\n")


def test_pinned_input_digest_and_output_independence(builder, tmp_path):
    source = tmp_path / "contractors.csv"
    output = tmp_path / "jackups.csv"
    raw = source_csv(builder)
    source.write_bytes(raw)
    output.write_text("Unrelated previous output\n", encoding="utf-8", newline="\n")
    digest = hashlib.sha256(raw).hexdigest()
    assert builder.main([str(source), str(output), "--source-sha256", digest]) == 0
    assert output.read_bytes() == builder.build_csv(raw)
    expected = output.read_bytes()
    with pytest.raises(ValueError, match="digest"):
        builder.main([str(source), str(output), "--source-sha256", "0" * 64])
    assert output.read_bytes() == expected
    with pytest.raises(ValueError, match="distinct"):
        builder.main([str(source), str(source), "--source-sha256", digest])
    assert source.read_bytes() == raw


def test_committed_dataset_matches_schema_and_provenance():
    rebuild = (
        "python scripts/field_development/build_contractor_jackups.py "
        "<contractor-collection.csv> <replacement.csv> --source-sha256 <digest>"
    )
    path = DATA / "curated/jackups.csv"
    raw = path.read_bytes()
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))
    schema = yaml.safe_load((DATA / "schema.yaml").read_text(encoding="utf-8"))
    contract = next(d for d in schema["datasets"] if d["name"] == path.name)
    metadata = json.loads((DATA / "_metadata.json").read_text(encoding="utf-8"))
    entry = next(d for d in metadata["files"] if d["name"] == path.name)
    assert len(rows) == contract["row_count"] == entry["row_count"] == 163
    assert len({r["RIG_NAME"].casefold() for r in rows}) == len(rows)
    assert list(rows[0]) == [c["name"] for c in contract["columns"]]
    assert all(r["source_url"] for r in rows)
    assert all(r[key] == "" for r in rows for key in UNAVAILABLE)
    assert contract["size_bytes"] == entry["size_bytes"] == len(raw)
    assert (
        entry["sha256"] == hashlib.sha256(raw).hexdigest()
    ), f"Verify the retained input before rebuilding with: {rebuild}"
    provenance = entry["provenance"]
    assert provenance["retrieved"] == "2026-10-27"
    assert (
        provenance["source_sha256"]
        == "1618e8f01b438221919fb5e3c5f7d33b945743d9d992d018a1489a91430e34b9"
    ), f"Verify the original collection digest before running: {rebuild}"
    assert provenance["source_row_count"] == len(rows)
    assert sorted(provenance["unavailable_columns"]) == sorted(UNAVAILABLE)
    assert "source_url" not in UNAVAILABLE
    numeric = [c for c in contract["columns"] if c["type"] in {"float", "integer"}]
    for row in rows:
        for column in numeric:
            value = row[column["name"]]
            if value:
                number = int(value) if column["type"] == "integer" else float(value)
                assert number > 0
