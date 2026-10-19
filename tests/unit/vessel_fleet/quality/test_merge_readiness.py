"""Readiness counts use independently enumerated synthetic sets.

No physical ratings or acceptance tolerances are assumed. Fixture labels are
synthetic; field presence is tested separately from engineering validity.
"""

import json
from copy import deepcopy

import pytest

from worldenergydata.vessel_fleet.quality.merge_readiness import (
    assess_merge_readiness,
    main,
)


def row(name, **fields):
    return {"VESSEL_NAME": name, **fields}


def test_equal_row_count_does_not_hide_lost_names():
    """Hand calculation: {A,B} - {B,C} = {A}; intersection = {B}."""
    baseline = [row("Synthetic A"), row("Synthetic B")]
    candidate = [row("Synthetic B"), row("Synthetic C")]
    result = assess_merge_readiness(baseline, candidate)
    assert result["name_coverage"] == {
        "status": "BLOCKED",
        "baseline_unique_names": 2,
        "candidate_unique_names": 2,
        "retained_names": 1,
        "added_names": 1,
        "removed_names": 1,
        "baseline_unnamed_rows": 0,
        "candidate_unnamed_rows": 0,
        "baseline_duplicate_names": 0,
        "candidate_duplicate_names": 0,
    }


def test_normalization_and_additions_preserve_coverage_without_mutation():
    """A repeated case/spacing variant retains A; B adds one unique name."""
    baseline = [row("Synthetic A")]
    candidate = [row(" synthetic   a "), row("Synthetic B")]
    before = deepcopy((baseline, candidate))
    result = assess_merge_readiness(baseline, candidate)
    assert result["name_coverage"]["status"] == "PASS"
    assert result["name_coverage"]["retained_names"] == 1
    assert result["name_coverage"]["added_names"] == 1
    assert (baseline, candidate) == before
    assert result["field_presence"]["status"] == "NOT_EVALUATED"
    assert result["engineering_validity"] == "NOT_EVALUATED"


@pytest.mark.parametrize(
    "baseline,candidate",
    [
        (None, [row("Synthetic A")]),
        ([], [row("Synthetic A")]),
        ([row("Synthetic A")], []),
        ([row(None)], [row("Synthetic A")]),
        ([row("Synthetic A")], [row("Synthetic A"), row(" ")]),
        ([row("Synthetic A"), row("synthetic a")], [row("Synthetic A")]),
        ([row("Synthetic A")], [row("Synthetic A"), row("synthetic a")]),
    ],
)
def test_incomplete_or_ambiguous_identity_is_not_evaluated(baseline, candidate):
    """Empty sets, unnamed rows and duplicate normalized names deny certainty."""
    assert (
        assess_merge_readiness(baseline, candidate)["name_coverage"]["status"]
        == "NOT_EVALUATED"
    )


def test_missing_fields_include_blank_null_and_nonfinite_but_not_zero():
    """Five A-E rows: only zero is present, hence four missing ratings."""
    candidate = [
        row(f"Synthetic {name}", RATING=value)
        for name, value in zip("ABCDE", [None, " ", float("nan"), float("inf"), 0])
    ]
    result = assess_merge_readiness(candidate, candidate, required_fields=("RATING",))
    assert result["field_presence"] == {
        "status": "BLOCKED",
        "missing_by_field": {"RATING": 4},
    }
    json.dumps(result, allow_nan=False)


def test_absent_columns_are_counted_per_row():
    """Two rows without DESIGN give two missing cells, not a KeyError."""
    candidate = [row("Synthetic A"), row("Synthetic B")]
    result = assess_merge_readiness(candidate, candidate, required_fields=("DESIGN",))
    assert result["field_presence"]["missing_by_field"] == {"DESIGN": 2}


def test_no_candidate_cannot_pass_field_presence():
    result = assess_merge_readiness([], [], required_fields=("DESIGN",))
    assert result["field_presence"]["status"] == "NOT_EVALUATED"


def test_cli_reads_only_raw_parquet_and_curated_baseline(tmp_path, capsys):
    """Raw A+A+B deduplicates to A+B; curated A+C loses C and gains B."""
    import pandas as pd

    raw = tmp_path / "raw" / "spec_details"
    raw.mkdir(parents=True)
    curated = tmp_path / "curated"
    curated.mkdir()
    pd.DataFrame(
        [
            row("Synthetic A", VESSEL_CATEGORY="drilling_rig", DESIGN="example"),
            row("Synthetic A", VESSEL_CATEGORY="drilling_rig"),
            row("Synthetic B", VESSEL_CATEGORY="drilling_rig", DESIGN="example"),
            row("Synthetic D", VESSEL_CATEGORY="construction_vessel"),
        ]
    ).to_parquet(raw / "input.parquet", index=False)
    pd.DataFrame([row("Synthetic A"), row("Synthetic C")]).to_csv(
        curated / "drilling_rigs.csv", index=False
    )
    before = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert main(["--data-dir", str(tmp_path), "--required-field", "DESIGN"]) == 2
    report = json.loads(capsys.readouterr().out)
    assert report["raw_records"] == 4
    assert report["candidate_rows"] == 2
    assert report["name_coverage"]["removed_names"] == 1
    assert report["field_presence"]["status"] == "PASS"
    after = {
        p.relative_to(tmp_path): p.read_bytes()
        for p in tmp_path.rglob("*")
        if p.is_file()
    }
    assert after == before


def test_cli_missing_directory_does_not_create_it(tmp_path, capsys):
    missing = tmp_path / "missing"
    assert main(["--data-dir", str(missing)]) == 3
    assert (
        json.loads(capsys.readouterr().out)["name_coverage"]["status"]
        == "NOT_EVALUATED"
    )
    assert not missing.exists()


def test_cli_pass_is_limited_to_explicit_checks(tmp_path, capsys):
    import pandas as pd

    raw = tmp_path / "raw" / "source"
    raw.mkdir(parents=True)
    curated = tmp_path / "curated"
    curated.mkdir()
    records = [row("Synthetic A", VESSEL_CATEGORY="drilling_rig", DESIGN="example")]
    pd.DataFrame(records).to_parquet(raw / "input.parquet", index=False)
    pd.DataFrame(records).to_csv(curated / "drilling_rigs.csv", index=False)
    assert main(["--data-dir", str(tmp_path), "--required-field", "DESIGN"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["engineering_validity"] == "NOT_EVALUATED"


def test_cli_unreadable_input_fails_without_results(tmp_path, capsys):
    raw = tmp_path / "raw" / "source"
    raw.mkdir(parents=True)
    (raw / "input.parquet").write_text("not parquet")
    assert main(["--data-dir", str(tmp_path)]) == 2
    output = capsys.readouterr()
    assert not output.out
    assert "Unable to read assessment inputs" in output.err


def test_cli_missing_baseline_with_recursive_raw_sources(tmp_path, capsys):
    """Two distinct source rows form A+B; missing baseline denies comparison."""
    import pandas as pd

    for directory, name in [
        ("source_a/nested", "Synthetic A"),
        ("source_b", "Synthetic B"),
    ]:
        source = tmp_path / "raw" / directory
        source.mkdir(parents=True)
        pd.DataFrame([row(name, VESSEL_CATEGORY="drilling_rig")]).to_parquet(
            source / "input.parquet", index=False
        )
    assert main(["--data-dir", str(tmp_path)]) == 3
    report = json.loads(capsys.readouterr().out)
    assert report["baseline_rows"] is None
    assert report["candidate_rows"] == 2
    assert report["source_rows"] == {
        "source_a/nested/input.parquet": 1,
        "source_b/input.parquet": 1,
    }
    assert not (tmp_path / "curated").exists()


def test_known_loss_blocks_even_when_other_names_are_unusable():
    """{A,B} minus {B} loses A despite an additional unnamed candidate row."""
    result = assess_merge_readiness(
        [row("Synthetic A"), row("Synthetic B")],
        [row("Synthetic B"), row(None)],
    )
    assert result["name_coverage"]["status"] == "BLOCKED"
    assert result["name_coverage"]["removed_names"] == 1
