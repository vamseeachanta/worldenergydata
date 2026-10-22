"""Atlas evidence regressions; synthetic expectations are hand-calculated below."""

import csv
import importlib.util
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "all_regions_atlas", ROOT / "scripts/field_development/build_all_regions_atlas.py"
)
atlas = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(atlas)


def test_csv_count_handles_quoted_newlines_and_blank_records(tmp_path):
    """Hand count: two data records; the embedded newline adds no CSV record."""
    source = tmp_path / "rows.csv"
    source.write_text(
        'name,note\nalpha,"first\nsecond"\n\nbeta,end\n',
        encoding="utf-8",
        newline="\n",
    )
    assert atlas.count_data_rows(source) == 2


def test_absent_evidence_is_not_zero(tmp_path):
    """Zero CSV records do not establish an observed GoM field population."""
    source = tmp_path / "absent.csv"
    assert atlas.count_data_rows(source) is None
    assert atlas.count_glob_html(tmp_path / "absent") is None
    assert atlas.gom_atlas_counts(source) == (None, None)
    source.write_text("FIELD_CODE,WELL_COUNT\n", encoding="utf-8", newline="\n")
    assert atlas.count_data_rows(source) == 0
    assert atlas.gom_atlas_counts(source) == (None, None)
    assert atlas.count_glob_html(tmp_path) == 0


def test_gom_counts_use_export_schema(tmp_path):
    """Hand calculation: two field codes; per-field well memberships = 2 + 3 = 5.

    Schema source: AllFieldsRunner._compute_field_production in all_fields_runner.py.
    The sum is not a basin-wide unique well count: a well may cross fields.
    """
    source = tmp_path / "gom.csv"
    source.write_text(
        "FIELD_CODE,WELL_COUNT\nA,2\nB,3\n", encoding="utf-8", newline="\n"
    )
    assert atlas.gom_atlas_counts(source) == (2, 5)


def test_html_page_counts_exclude_directories_and_templates(tmp_path):
    """Hand count: one content file; index, template, and directory do not count."""
    for name in ("index.html", "lifecycle_template.html", "content.html"):
        (tmp_path / name).write_text("<html></html>", encoding="utf-8", newline="\n")
    (tmp_path / "folder.html").mkdir()
    assert (
        atlas.count_glob_html(
            tmp_path, exclude={"index.html", "lifecycle_template.html"}
        )
        == 1
    )


def test_geographic_scope_requires_available_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(atlas, "CENTROIDS_CSV", tmp_path / "absent.csv")
    with pytest.raises(ValueError, match="Geographic atlas"):
        atlas.centroid_country_count()


@pytest.mark.parametrize(
    "body",
    [
        "FIELD_CODE,WELL_COUNT\nA,-1\n",
        "FIELD_CODE,WELL_COUNT\nA,2.5\n",
        "FIELD_CODE,WELL_COUNT\nA,\n",
        "FIELD_CODE,WELL_COUNT\n,2\n",
        "FIELD_CODE,WELL_COUNT\nA,2\nA,3\n",
        "FIELD_CODE\nA\n",
        "",
    ],
)
def test_invalid_gom_counts_fail_closed(tmp_path, body):
    """Counts require nonnegative integers and exactly one row per field code."""
    source = tmp_path / "gom.csv"
    source.write_text(body, encoding="utf-8", newline="\n")
    with pytest.raises(ValueError):
        atlas.gom_atlas_counts(source)


def sample_rows():
    # Synthetic records: density = facilities / fields = 3 / 2 = 1.5.
    return [
        {
            "country": "US",
            "fields": 2,
            "facilities": 3,
            "badge": "RICH",
            "module": "bsee",
            "catalog_status": "sample",
        },
        {
            "country": "UK",
            "fields": 0,
            "facilities": 1,
            "badge": "ROADMAP",
            "module": "ukcs",
            "catalog_status": "runtime_fetched",
        },
    ]


def render(rows=None):
    return atlas.build_html(
        rows if rows is not None else sample_rows(),
        {},
        {"fields": 2, "facilities": 4},
        2,
        2,
        1,
        dict.fromkeys(("fields", "wells", "matched", "bench", "lifecycle")),
    )


def map_trace(text):
    match = re.search(
        r'<script id="atlas-map-data" type="application/json">(.*?)</script>',
        text,
        re.DOTALL,
    )
    assert match, "choropleth data must be embedded without a runtime data request"
    return json.loads(match.group(1))


def test_map_uses_table_counts_and_preserves_zero():
    """Direct enumeration: two locations, field counts [2, 0], facilities [3, 1]."""
    trace = map_trace(render())
    assert trace["type"] == "choropleth"
    assert trace["locationmode"] == "country names"
    assert trace["locations"] == ["United States", "United Kingdom"]
    assert trace["z"] == [2, 0]
    assert trace["customdata"] == [[3, "RICH"], [1, "ROADMAP"]]


def test_map_loads_supported_plotly_build_with_integrity():
    """The rendered dependency uses the repository's supported build and CDN digest."""
    text = render()
    script = re.search(r'<script src="([^"]+)"([^>]*)></script>', text)
    assert script is not None
    assert script.group(1) == "https://cdn.plot.ly/plotly-2.35.2.min.js"
    # SHA-384 of the published 2.35.2 bytes, retrieved independently from the CDN.
    assert (
        'integrity="sha384-cCVCZkAjYNxaYKbM8lsArLznDF/SvMFr1jcZrvOpSTCa0W40ZAdLzHCEulnUa5i7"'
        in script.group(2)
    )
    assert 'crossorigin="anonymous"' in script.group(2)


def test_observed_gom_field_can_have_zero_wells(tmp_path):
    """One recorded field with zero memberships differs from unavailable evidence."""
    source = tmp_path / "gom.csv"
    source.write_text("FIELD_CODE,WELL_COUNT\nA,0\n", encoding="utf-8", newline="\n")
    assert atlas.gom_atlas_counts(source) == (1, 0)


def test_non_utf8_benchmark_fails_closed(tmp_path):
    source = tmp_path / "rows.csv"
    source.write_bytes(b"name\n\xff\n")
    with pytest.raises(UnicodeDecodeError):
        atlas.count_data_rows(source)


def test_map_data_cannot_terminate_script():
    """A literal closing script tag must never escape the embedded JSON element."""
    rows = sample_rows()
    rows[0]["country"] = '</script><img src=x onerror="alert(1)">'
    text = render(rows)
    assert map_trace(text)["locations"][0] == rows[0]["country"]
    assert '<img src=x onerror="alert(1)">' not in text


def test_render_explains_missing_evidence_and_badge_override():
    text = render()
    assert "NOT_EVALUATED" in text
    assert "~1,390" not in text and "~30k" not in text
    assert ">None<" not in text
    assert "Catalog status" in text
    assert "runtime_fetched" in text
    assert "GoM-only override" in text
    assert "country-wide" in text
    assert "Revision history" in text
    assert "1.50" in text  # Hand calculation: 3 facilities / 2 fields.
    assert "Map unavailable" in text
    assert "Unshaded" in text


def test_empty_and_zero_catalogs_render():
    """No positive counts means zero-width bars, never division by zero."""
    assert map_trace(render([]))["z"] == []
    rows = sample_rows()
    rows[0]["fields"] = 0
    assert map_trace(render(rows))["z"] == [0, 0]


def test_main_writes_real_source_counts_and_preserves_badges(tmp_path, monkeypatch):
    """Expected rows and totals are read independently from the cited source CSV.

    Badge expectations use the shared catalog contract, not this generator.
    """
    html_path, csv_path = tmp_path / "atlas.html", tmp_path / "coverage.csv"
    monkeypatch.setattr(atlas, "OUT_HTML", html_path)
    monkeypatch.setattr(atlas, "OUT_CSV", csv_path)
    atlas.main()
    with atlas.COVERAGE_CSV.open(newline="", encoding="utf-8") as handle:
        source = {
            r[1]: (int(r[2]), int(r[3]))
            for r in csv.reader(handle)
            if r and r[0] == "by_country"
        }
    with csv_path.open(newline="", encoding="utf-8") as handle:
        result = list(csv.DictReader(handle))
    assert {
        r["country"]: (int(r["fields"]), int(r["facilities"])) for r in result
    } == source
    statuses = atlas.load_scorecard(atlas.SCORECARD)
    for row in result:
        assert (
            row["badge"],
            row["source_module"],
            row["catalog_status"],
        ) == atlas.badge_for(row["country"], statuses)
    trace = map_trace(html_path.read_text(encoding="utf-8"))
    assert sorted(trace["z"]) == sorted(value[0] for value in source.values())
