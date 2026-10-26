"""Pipe lookup tests using invented geometry, never a pipe schedule table."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd
import pytest
import yaml

from worldenergydata.bsee.pipeline.spec_lookup import PipelineSpecLookup

COLUMNS = [
    "nps_in",
    "od_mm",
    "od_in",
    "schedule",
    "wt_mm",
    "wt_in",
    "weight_kgm",
    "grade_range",
    "standard",
    "domain_hint",
]
DATA_DIR = Path(__file__).resolve().parents[4] / "data/modules/pipeline"


def write_sources(folder, count=5):
    """Invented provenance for invented test inputs; unsuitable for studies."""
    sources = {
        "version": 1,
        "rows": [
            {
                "row": row,
                "kind": "synthetic",
                "title": "Synthetic pipe lookup fixture",
                "publisher": "Test fixture",
                "catalogue_number": "synthetic-geometry",
                "revision": "1",
                "date": "2026-10-26",
            }
            for row in range(1, count + 1)
        ],
    }
    (folder / "sources.yml").write_text(yaml.safe_dump(sources))
    return sources


@pytest.fixture
def sample_schedule_data(tmp_path):
    """Arbitrary dimensions and labels, generated solely for these tests."""
    rows = []
    for nps, od, schedule, wt, domain in [
        (7, 201, "TEST_THIN", 8, "test_infield"),
        (7, 201, "TEST_THICK", 14, "test_infield"),
        (9, 251, "TEST_THIN", 11, "test_infield"),
        (13, 351, "TEST_THIN", 12, "test_export"),
        (17, 451, "TEST_BORE", 18, "test_riser"),
    ]:
        # Annulus area times an invented test density; mm² converted to m².
        mass = math.pi * wt * (od - wt) * 1e-6 * 7700
        rows.append(
            (
                nps,
                od,
                od / 25.4,
                schedule,
                wt,
                wt / 25.4,
                mass,
                "TEST_LOW-TEST_HIGH",
                "Synthetic fixture",
                domain,
            )
        )
    pd.DataFrame(rows, columns=COLUMNS).to_csv(
        tmp_path / "api_5l_pipe_schedule.csv", index=False
    )
    write_sources(tmp_path)
    return tmp_path


def fixture_lookup(folder):
    return PipelineSpecLookup(data_dir=folder, allow_synthetic=True)


class TestPipelineSpecLookupBasics:
    def test_load_returns_dataframe(self, sample_schedule_data):
        df = fixture_lookup(sample_schedule_data).load()
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 5

    def test_missing_data_returns_empty(self, tmp_path):
        assert PipelineSpecLookup(data_dir=tmp_path / "absent").load().empty

    def test_caches_on_second_load(self, sample_schedule_data):
        lookup = fixture_lookup(sample_schedule_data)
        assert lookup.load() is lookup.load()

    def test_get_all_nps_sizes(self, sample_schedule_data):
        assert fixture_lookup(sample_schedule_data).get_all_nps_sizes() == [
            7,
            9,
            13,
            17,
        ]

    def test_nps_summary(self, sample_schedule_data):
        assert fixture_lookup(sample_schedule_data).nps_summary()[7] == [
            "TEST_THIN",
            "TEST_THICK",
        ]

    def test_get_by_nps(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).get_by_nps(7)
        assert len(result) == 2
        assert all(result["nps_in"] == 7)


class TestPipelineSpecLookupMatchOdWt:
    def test_match_od_exact(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.201, 0.008)
        assert result["nps_in"] == 7
        assert result["schedule"] == "TEST_THIN"

    def test_match_od_approximate(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.2011, 0.012)
        assert result["nps_in"] == 7

    def test_match_schedule_by_wt(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.201, 0.014)
        assert result["schedule"] == "TEST_THICK"

    def test_match_bore(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.451, 0.018)
        assert result["nps_in"] == 17
        assert result["domain_hint"] == "test_riser"

    def test_no_match_far_od(self, sample_schedule_data):
        assert fixture_lookup(sample_schedule_data).match_od_wt(0.1, 0.01) is None

    def test_result_has_required_keys(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.201, 0.008)
        assert set(COLUMNS + ["source", "provenance"]) <= result.keys()

    def test_result_source_attribution(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.201, 0.008)
        assert "PipelineSpecLookup" in result["source"]
        assert result["provenance"]["title"] == "Synthetic pipe lookup fixture"
        assert result["provenance"]["row"] == 1

    def test_match_od_only_zero_wt(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.201)
        assert result["schedule"] == "TEST_THIN"

    def test_grade_range_is_list(self, sample_schedule_data):
        result = fixture_lookup(sample_schedule_data).match_od_wt(0.201, 0.008)
        assert result["grade_range"] == ["TEST_LOW", "TEST_HIGH"]

    def test_empty_data_returns_none(self, tmp_path):
        assert PipelineSpecLookup(data_dir=tmp_path).match_od_wt(0.201) is None


class TestPipelineSpecLookupIntegration:
    """The distributed template must never silently supply engineering values."""

    def test_distributed_csv_is_header_only(self):
        assert pd.read_csv(DATA_DIR / "api_5l_pipe_schedule.csv").empty

    def test_default_match_requires_supplied_data(self):
        assert PipelineSpecLookup().match_od_wt(0.201, 0.008) is None

    def test_default_bore_match_requires_supplied_data(self):
        assert PipelineSpecLookup().match_od_wt(0.451, 0.018) is None

    def test_default_summary_is_empty(self):
        assert PipelineSpecLookup().nps_summary() == {}
        assert PipelineSpecLookup().get_all_nps_sizes() == []
        assert PipelineSpecLookup().get_by_nps(7).empty

    def test_no_standards_attributed_sources_in_distributed_data(self):
        from worldenergydata.bsee.pipeline.spec_lookup import validate_source_label

        df = pd.read_csv(DATA_DIR / "api_5l_pipe_schedule.csv")
        manifest = yaml.safe_load((DATA_DIR / "sources.yml").read_text())
        for label in df["standard"]:
            validate_source_label(label)
        for source in manifest["rows"]:
            for field in ("title", "publisher", "url", "catalogue_number"):
                validate_source_label(source.get(field, ""))
        assert len(manifest["rows"]) == len(df)
        assert PipelineSpecLookup(data_dir=DATA_DIR).load().empty

    def test_import_from_bsee_pipeline(self):
        from worldenergydata.bsee.pipeline import PipelineSpecLookup as PSL

        assert isinstance(PSL(), PipelineSpecLookup)


@pytest.mark.parametrize(
    "column,value",
    [
        ("od_mm", 0),
        ("wt_mm", -1),
        ("wt_mm", 101),
        ("od_mm", float("inf")),
        ("wt_mm", float("nan")),
        ("nps_in", "invalid"),
        ("nps_in", 0),
        ("od_in", 999),
        ("wt_in", 999),
        ("weight_kgm", -1),
        ("weight_kgm", float("inf")),
        ("schedule", ""),
        ("standard", "API 5L / ASME B36.10M"),
    ],
)
def test_invalid_rows_are_rejected(sample_schedule_data, column, value):
    path = sample_schedule_data / "api_5l_pipe_schedule.csv"
    df = pd.read_csv(path).astype({column: object})
    df.loc[0, column] = value
    df.to_csv(path, index=False)
    with pytest.raises(ValueError):
        fixture_lookup(sample_schedule_data).load()


@pytest.mark.parametrize(
    "field",
    ["row", "kind", "title", "publisher", "catalogue_number", "revision", "date"],
)
def test_missing_provenance_is_rejected(sample_schedule_data, field):
    manifest = write_sources(sample_schedule_data)
    del manifest["rows"][0][field]
    (sample_schedule_data / "sources.yml").write_text(yaml.safe_dump(manifest))
    with pytest.raises(ValueError):
        fixture_lookup(sample_schedule_data).load()


@pytest.mark.parametrize(
    "label",
    [
        "API 5L",
        "API STD 16F",
        "ASME B36.10M",
        "ISO 3183",
        "ASTM A106",
        "American Petroleum Institute",
        "American Society of Mechanical Engineers",
        "International Organization for Standardization",
        "ANSI",
        "BS EN 10220",
    ],
)
def test_standards_attribution_is_rejected(sample_schedule_data, label):
    manifest = write_sources(sample_schedule_data)
    manifest["rows"][0]["title"] = label
    (sample_schedule_data / "sources.yml").write_text(yaml.safe_dump(manifest))
    with pytest.raises(ValueError, match="standard"):
        fixture_lookup(sample_schedule_data).load()


@pytest.mark.parametrize(
    "case",
    [
        "absent",
        "malformed",
        "missing_row",
        "duplicate_row",
        "extra_row",
        "bad_date",
        "bad_url",
        "bad_kind",
        "bad_version",
        "duplicate_key",
    ],
)
def test_invalid_manifest_is_rejected(sample_schedule_data, case):
    manifest = write_sources(sample_schedule_data)
    path = sample_schedule_data / "sources.yml"
    if case == "absent":
        path.rename(sample_schedule_data / "unused.yml")
    elif case == "malformed":
        path.write_text("rows: [")
    elif case == "duplicate_key":
        path.write_text("version: 1\nrows: []\nrows: []\n")
    else:
        if case == "missing_row":
            manifest["rows"].pop()
        elif case == "duplicate_row":
            manifest["rows"][1]["row"] = 1
        elif case == "extra_row":
            manifest["rows"].append({**manifest["rows"][0], "row": 6})
        elif case == "bad_date":
            manifest["rows"][0]["date"] = "not-a-date"
        elif case == "bad_url":
            del manifest["rows"][0]["catalogue_number"]
            manifest["rows"][0]["url"] = "file:fixture"
        elif case == "bad_kind":
            manifest["rows"][0]["kind"] = "standard"
        elif case == "bad_version":
            manifest["version"] = 2
        path.write_text(yaml.safe_dump(manifest))
    with pytest.raises(ValueError):
        fixture_lookup(sample_schedule_data).load()


def test_missing_column_is_rejected(sample_schedule_data):
    path = sample_schedule_data / "api_5l_pipe_schedule.csv"
    pd.read_csv(path).drop(columns="od_mm").to_csv(path, index=False)
    with pytest.raises(ValueError):
        fixture_lookup(sample_schedule_data).load()


def test_synthetic_data_requires_explicit_opt_in(sample_schedule_data):
    with pytest.raises(ValueError, match="synthetic"):
        PipelineSpecLookup(data_dir=sample_schedule_data).load()


@pytest.mark.parametrize("kind", ["manufacturer", "public_paper", "design_basis"])
def test_caller_supplied_provenance_is_returned(sample_schedule_data, kind):
    # These remain invented test records, merely exercising accepted categories.
    manifest = write_sources(sample_schedule_data)
    for source in manifest["rows"]:
        source["kind"] = kind
    (sample_schedule_data / "sources.yml").write_text(yaml.safe_dump(manifest))
    result = PipelineSpecLookup(data_dir=sample_schedule_data).match_od_wt(0.201)
    assert result["provenance"]["kind"] == kind


def test_optional_values_remain_optional(sample_schedule_data):
    path = sample_schedule_data / "api_5l_pipe_schedule.csv"
    df = pd.read_csv(path)
    df.loc[0, ["weight_kgm", "grade_range", "domain_hint", "standard"]] = None
    df.to_csv(path, index=False)
    result = fixture_lookup(sample_schedule_data).match_od_wt(0.201)
    assert result["weight_kgm"] is None
    assert result["grade_range"] == []
    assert result["domain_hint"] is None


def test_wt_fallback_is_preserved(sample_schedule_data):
    result = fixture_lookup(sample_schedule_data).match_od_wt(0.201, 0.04)
    assert result["schedule"] == "TEST_THICK"


def test_manifest_rejects_python_object_tags(sample_schedule_data):
    (sample_schedule_data / "sources.yml").write_text("!!python/tuple [1, 2]")
    with pytest.raises(ValueError):
        fixture_lookup(sample_schedule_data).load()
