"""Snapshot checks use synthetic counts, independently added in each fixture."""

import csv
import json

import pytest
from lower_tertiary import dc_surface_audit as surfaces


@pytest.fixture
def snapshots(tmp_path):
    """Two bores: D=6+0=6, C=10+0=10, D&C=16, two bores total.

    These are arbitrary test inputs, not measured data or acceptance limits.
    Every format is written independently of the checker and generators.
    """
    bores = [
        {
            "api12": api,
            "development": "synthetic",
            "before": {"drilling_days": d, "completion_days": c, "dc_days": d + c},
        }
        for api, d, c in [("100000000001", 6, 10), ("100000000002", 0, 0)]
    ]
    for path in surfaces.LOCAL_SURFACES.values():
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / surfaces.LOCAL_SURFACES["validation"]).write_text(
        "| Development | WED bores | WED D&C |\n|---|---:|---:|\n"
        "| **synthetic** | **2** | **16** |\n",
        encoding="utf-8",
    )
    (tmp_path / surfaces.LOCAL_SURFACES["listing"]).write_text(
        "| Development | Bores (wed) | Drilling | Completion | D&C (wed) |\n"
        "|---|---:|---:|---:|---:|\n| [synthetic](#synthetic) | 2 | 6 | 10 | 16 |\n\n"
        "| API12 | Drilling | Completion | D&C |\n|---|---:|---:|---:|\n"
        "| 100000000001 | 6 | 10 | 16 |\n| 100000000002 | 0 | 0 | 0 |\n",
        encoding="utf-8",
    )
    payload = {
        "bores": [
            {"api": b["api12"], "field": "synthetic", "drill": d, "compl": c}
            for b, d, c in [(bores[0], 6, 10), (bores[1], 0, 0)]
        ],
        "fields": [{"name": "synthetic", "bores": 2, "drill": 6, "compl": 10}],
    }
    (tmp_path / surfaces.LOCAL_SURFACES["drilldown"]).write_text(
        "<script>\nconst DATA = " + json.dumps(payload) + ";\n</script>\n",
        encoding="utf-8",
    )
    with (tmp_path / surfaces.LOCAL_SURFACES["vintage"]).open("w") as stream:
        writer = csv.DictWriter(
            stream, fieldnames=["api12", "dev", "drill_wed", "compl_wed"]
        )
        writer.writeheader()
        writer.writerows(
            {"api12": b["api12"], "dev": "synthetic", "drill_wed": d, "compl_wed": c}
            for b, d, c in [(bores[0], 6, 10), (bores[1], 0, 0)]
        )
    return tmp_path, bores


def test_matching_local_counts_do_not_certify_external_publication(snapshots):
    result = surfaces.audit_surfaces(*snapshots)
    assert result["status"] == "NOT_EVALUATED"
    assert result["local_status"] == "MATCH"
    assert [s["status"] for s in result["surfaces"]] == ["MATCH"] * 4 + [
        "NOT_EVALUATED",
        "NOT_EVALUATED",
    ]
    for snapshot in result["surfaces"][:4]:
        assert len(snapshot["sha256"]) == 64
        assert snapshot["findings"] == []
        assert not snapshot["path"].startswith("/")


@pytest.mark.parametrize(
    "surface,old,new",
    [
        ("validation", "**16**", "**17**"),
        ("listing", "| 2 | 6 | 10 | 16 |", "| 2 | 6 | 10 | 17 |"),
        ("listing", "| 100000000001 | 6 |", "| 100000000001 | 7 |"),
        ("drilldown", '"drill": 6', '"drill": 7'),
        ("drilldown", '"bores": 2', '"bores": 3'),
        ("vintage", ",6,10", ",7,10"),
        ("vintage", "100000000001,synthetic", "100000000001,other"),
    ],
)
def test_stale_bore_and_development_counts_are_reported(snapshots, surface, old, new):
    root, bores = snapshots
    path = root / surfaces.LOCAL_SURFACES[surface]
    text = path.read_text()
    assert old in text
    path.write_text(text.replace(old, new))
    result = surfaces.audit_surfaces(root, bores)
    assert result["local_status"] == "MISMATCH"
    snapshot = next(s for s in result["surfaces"] if s["surface"] == surface)
    assert snapshot["status"] == "MISMATCH"
    assert snapshot["findings"]


@pytest.mark.parametrize("problem", ["missing", "extra", "duplicate", "invalid"])
def test_population_or_malformed_snapshot_cannot_match(snapshots, problem):
    root, bores = snapshots
    path = root / surfaces.LOCAL_SURFACES["vintage"]
    content = path.read_text()
    row = "100000000001,synthetic,6,10\n"
    if problem == "missing":
        content = content.replace(row, "")
    elif problem == "extra":
        content += "100000000003,synthetic,0,0\n"
    elif problem == "duplicate":
        content += row
    else:
        content = content.replace(",6,10", ",nan,10")
    path.write_text(content)
    result = surfaces.audit_surfaces(root, bores)
    assert result["local_status"] == "MISMATCH"
    assert result["surfaces"][3]["status"] in {"MISMATCH", "INVALID"}


def test_missing_snapshots_stay_not_evaluated(tmp_path):
    result = surfaces.audit_surfaces(tmp_path, [])
    assert result["local_status"] == "NOT_EVALUATED"
    assert all(s["status"] == "NOT_EVALUATED" for s in result["surfaces"])


def test_nulls_are_not_compared_as_zero(snapshots):
    root, bores = snapshots
    bores[1]["before"] = dict.fromkeys(bores[1]["before"])
    result = surfaces.audit_surfaces(root, bores)
    assert result["local_status"] == "MISMATCH"
    assert result["surfaces"][0]["findings"][0]["expected"] is None


@pytest.mark.parametrize("duplicate", ["api12", "dev", "drill_wed", "compl_wed"])
def test_duplicate_csv_headers_cannot_match(snapshots, duplicate):
    root, bores = snapshots
    columns = ["api12", "dev", "drill_wed", "compl_wed"]
    position = columns.index(duplicate)
    columns.insert(position, duplicate)
    path = root / surfaces.LOCAL_SURFACES["vintage"]
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        for bore in bores:
            row = [
                bore["api12"],
                bore["development"],
                bore["before"]["drilling_days"],
                bore["before"]["completion_days"],
            ]
            row.insert(position, "999")  # Contradictory value hidden by DictReader.
            writer.writerow(row)
    result = surfaces.audit_surfaces(root, bores)
    assert result["surfaces"][3]["status"] == "INVALID"
    assert result["local_status"] == "MISMATCH"


@pytest.mark.parametrize("problem", ["truncated", "truncated_optional", "extra"])
def test_csv_row_width_must_match_header(snapshots, problem):
    root, bores = snapshots
    columns = ["api12", "dev", "drill_wed", "compl_wed"]
    rows = [["100000000001", "synthetic", 6, 10], ["100000000002", "synthetic", 0, 0]]
    if problem == "truncated_optional":
        columns.append("note")
        rows[1].append("synthetic note")
    elif problem == "truncated":
        rows[0].pop()
    else:
        rows[0].append("unexpected cell")
    path = root / surfaces.LOCAL_SURFACES["vintage"]
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(columns)
        writer.writerows(rows)
    result = surfaces.audit_surfaces(root, bores)
    assert result["surfaces"][3]["status"] == "INVALID"
    assert result["local_status"] == "MISMATCH"


def test_csv_allows_unique_additional_columns_with_complete_rows(snapshots):
    root, bores = snapshots
    path = root / surfaces.LOCAL_SURFACES["vintage"]
    lines = path.read_text().splitlines()
    path.write_text(lines[0] + ",note\n" + "\n".join(line + "," for line in lines[1:]))
    assert surfaces.audit_surfaces(root, bores)["surfaces"][3]["status"] == "MATCH"


@pytest.mark.parametrize("malformed", ["1,6", "16,", ",16", "0,16", "1,,6", "1,6.0"])
def test_malformed_numeric_grouping_cannot_match(snapshots, malformed):
    root, bores = snapshots
    path = root / surfaces.LOCAL_SURFACES["validation"]
    path.write_text(path.read_text().replace("**16**", f"**{malformed}**"))
    result = surfaces.audit_surfaces(root, bores)
    assert result["surfaces"][0]["status"] == "INVALID"
    assert result["local_status"] == "MISMATCH"


@pytest.mark.parametrize("malformed", ["1,23,456", "1,2345", "1234,567", "1,234e3"])
def test_invalid_thousands_groups_are_rejected(malformed):
    with pytest.raises(ValueError, match="snapshot count"):
        surfaces._number(malformed)


@pytest.mark.parametrize(
    "displayed,expected",
    [
        ("1,234", 1234),
        ("**1,234,567**", 1234567),
        (" *1,234.00* ", 1234),
        ("**16**", 16),
        ("0", 0),
        ("16.0", 16),
        ("", None),
        (None, None),
    ],
)
def test_valid_snapshot_numeric_formatting_is_preserved(displayed, expected):
    assert surfaces._number(displayed) == expected


def test_existing_artifacts_are_compared_without_running_generators():
    from pathlib import Path

    from lower_tertiary import build_dc_republication_audit as audit

    root = Path(__file__).resolve().parents[3]
    result = audit.build_audit(root)
    assert result["surface_agreement"]["local_status"] == "MATCH"
    assert result["surface_agreement"]["status"] == "NOT_EVALUATED"
