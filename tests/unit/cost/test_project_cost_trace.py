"""Portfolio trace tests; numerical examples are synthetic hand calculations.

No monetary constants are calibrated engineering inputs. Dates follow the
Gregorian calendar; expected counts are enumerations of the input rows.
"""

import csv
import json
from dataclasses import replace
from pathlib import Path

import pytest

from worldenergydata.cost.timeseries.portfolio_trace import (
    build_portfolio_trace,
    canonical_events,
    render_trace_html,
    write_trace_outputs,
)

CURATED = Path("data/modules/cost/curated")


def _tables(**changes):
    tables = {
        "sanctioned_projects.csv": [],
        "contract_awards.csv": [],
        "project_cost_statements.csv": [],
        "cost_revision_trails.csv": [],
    }
    tables.update(changes)
    return tables


def _trail(**changes):
    row = dict(
        PROJECT="Example development",
        STATEMENT_DATE="2020-02",
        VALUE_MM="100",
        CURRENCY="USD",
        KIND="sanction_estimate",
        BASIS="gross development",
        PROVENANCE="operator",
        CONFIDENCE="high",
        SOURCE_TITLE="Synthetic example",
        SOURCE_URL="https://example.org/evidence",
        QUOTED_TEXT="Synthetic 100",
    )
    row.update(changes)
    return row


def _build(rows):
    return build_portfolio_trace(tables=_tables(**{"cost_revision_trails.csv": rows}))


def test_order_precision_availability_and_missing_years():
    """Hand enumeration: 2020, 2022 and 2022 overlap; only 2021 is absent."""
    result = _build(
        [
            _trail(STATEMENT_DATE="2022", KIND="final_outturn"),
            _trail(),
            _trail(STATEMENT_DATE="2022-03", KIND="revised_estimate"),
        ]
    )
    assert [e.effective_date.label for e in result.events] == [
        "2020-02",
        "2022",
        "2022-03",
    ]
    assert result.events[0].effective_date.end.isoformat() == "2020-02-29"
    assert result.missing_years == {"Example development": [2021]}
    assert not result.events[1].definitely_before(result.events[2])
    assert all(not e.historical_feature_eligible for e in result.events)
    published = _build(
        [_trail(SOURCE_PUBLISHED_DATE="2023-01-02", ACCESSED_DATE="2024")]
    )
    assert published.events[0].source_available_date.label == "2023-01-02"
    assert published.events[0].historical_feature_eligible


def test_duplicate_events_deduplicate_but_conflicts_fail():
    """One row repeated twice is one observation; changing its value conflicts."""
    assert len(_build([_trail(), _trail()]).events) == 1
    with pytest.raises(ValueError, match="conflicting duplicate"):
        _build([_trail(), _trail(VALUE_MM="101")])


def test_native_lanes_basis_changes_and_no_cumulative_spend():
    """USD 100 and NOK 200 are two lanes, never a total of 300.

    Same-currency gross and net statements also remain separate observations.
    """
    result = _build(
        [
            _trail(),
            _trail(CURRENCY="NOK", VALUE_MM="200"),
            _trail(BASIS="net share", KIND="ownership_basis_change"),
        ]
    )
    assert len(result.lanes) == 3
    assert {e.currency for e in result.events} == {"USD", "NOK"}
    assert all(e.price_basis == "nominal" for e in result.events)
    assert result.consistency_status == "NOT_EVALUATED"
    assert {e.event_type for e in result.events} == {
        "sanction_estimate",
        "ownership_basis_change",
    }


def test_awards_preserve_range_band_unknown_currency_and_unlinked_scope():
    """Hand inputs: a 10–20 band and an undisclosed award imply no point sum."""
    rows = [
        dict(
            PROJECT="Example development",
            AWARD_YEAR="2020",
            CONTRACTOR="Supplier",
            ASSET_CLASS="surf",
            SCOPE_DESC="Package",
            VALUE_LOW_MM="10",
            VALUE_HIGH_MM="20",
            VALUE_BASIS="band",
            BAND_WORD="example",
            PROVENANCE="operator",
            SOURCE_TITLE="Synthetic",
            SOURCE_URL="https://example.org",
        ),
        dict(
            PROJECT="Example development",
            AWARD_YEAR="2022",
            CONTRACTOR="Supplier",
            ASSET_CLASS="host",
            SCOPE_DESC="Host",
            VALUE_LOW_MM="",
            VALUE_HIGH_MM="",
            VALUE_BASIS="not_public",
            PROVENANCE="operator",
        ),
    ]
    result = build_portfolio_trace(tables=_tables(**{"contract_awards.csv": rows}))
    band, missing = result.events
    assert (band.low_value, band.high_value, band.value_basis) == ("10", "20", "band")
    assert band.currency == "unknown"
    assert band.link_status == "unlinked"
    assert band.component == "surf"
    assert missing.low_value == missing.high_value == ""
    assert missing.value_basis == "not_public"
    with pytest.raises(ValueError, match="not_public"):
        build_portfolio_trace(
            tables=_tables(
                **{"contract_awards.csv": [{**rows[1], "VALUE_LOW_MM": "1"}]}
            )
        )


def test_trade_press_cannot_be_promoted_and_raw_range_is_not_laundered():
    """A curated 15 with a '10 to 20' quote is retained but unqualified."""
    result = _build(
        [
            _trail(
                PROVENANCE="trade_press",
                CONFIDENCE="high",
                VALUE_MM="15",
                QUOTED_TEXT="between 10 and 20",
            )
        ]
    )
    event = result.events[0]
    assert event.confidence == "low"
    assert event.bound_qualification == "NOT_EVALUATED"
    assert event.source_fields["QUOTED_TEXT"] == "between 10 and 20"
    assert event.low_value == event.high_value == "15"


def test_live_coverage_matches_union_and_pilot_links():
    tables = {}
    for name in _tables():
        with (CURATED / name).open(newline="", encoding="utf-8") as stream:
            tables[name] = list(csv.DictReader(stream))
    result = build_portfolio_trace(CURATED)
    expected = sorted({r["PROJECT"] for rows in tables.values() for r in rows})
    assert list(result.projects) == expected
    assert result.source_counts == {name: len(rows) for name, rows in tables.items()}
    assert {e.project for e in result.events} == set(expected)
    linked = [e for e in result.events if e.award_id]
    assert linked and all(e.requirement_ids for e in linked)
    assert any(e.currency == "NOK" for e in result.events)
    assert any(e.value_basis == "not_public" for e in result.events)
    assert result.trail_only_projects == sorted(
        {r["PROJECT"] for r in tables["cost_revision_trails.csv"]}
        - {r["PROJECT"] for r in tables["sanctioned_projects.csv"]}
    )


def test_outputs_are_deterministic_readable_and_escape_untrusted_text(tmp_path):
    """Two identical builds must have identical bytes; no clocks or host paths."""
    result = _build(
        [_trail(PROJECT="<script>alert(1)</script>", SOURCE_URL="javascript:alert(1)")]
    )
    html = render_trace_html(result)
    assert "<script>alert(1)</script>" not in html
    assert 'href="javascript:' not in html
    assert "&lt;script&gt;" in html
    first = write_trace_outputs(result, tmp_path / "first")
    second = write_trace_outputs(result, tmp_path / "second")
    assert {p.name: p.read_bytes() for p in first} == {
        p.name: p.read_bytes() for p in second
    }
    manifest = json.loads(first[-1].read_text())
    assert manifest["project_count"] == 1
    assert manifest["event_count"] == 1
    assert json.loads(canonical_events(result))[0]["source_fields"]["VALUE_MM"] == "100"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-1", "invalid"])
def test_invalid_monetary_values_fail(value):
    with pytest.raises(ValueError, match="amount"):
        _build([_trail(VALUE_MM=value)])


def test_input_digests_cover_all_consumed_tables_and_detect_changes(tmp_path):
    """Input bytes, including identity links, must determine the build provenance."""
    import shutil

    shutil.copytree(CURATED, tmp_path / "curated")
    result = build_portfolio_trace(tmp_path / "curated")
    assert "award_asset_links.csv" in result.input_sha256
    with (tmp_path / "curated" / "contract_awards.csv").open("a") as stream:
        stream.write("\n")
    changed = build_portfolio_trace(tmp_path / "curated")
    assert result.input_sha256 != changed.input_sha256
    assert canonical_events(result) == canonical_events(changed)


def test_output_rejects_tampered_result(tmp_path):
    result = _build([_trail()])
    with pytest.raises(ValueError, match="duplicate"):
        write_trace_outputs(replace(result, events=result.events * 2), tmp_path)


def test_builder_cli_writes_readable_outputs_and_protects_inputs(tmp_path):
    """CLI output counts must equal an independent union of input project names."""
    import os
    import subprocess
    import sys

    command = [
        sys.executable,
        "scripts/cost/build_project_cost_traces.py",
        "--data-root",
        str(CURATED),
        "--revision",
        "2",
        "--revision-date",
        "2026-10-20",
        "--output-dir",
        str(tmp_path),
    ]
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(key, None)
    run = subprocess.run(command, capture_output=True, text=True, env=env, check=True)
    manifest = json.loads((tmp_path / "project_trace_manifest.json").read_text())
    assert f"Projects: {manifest['project_count']}" in run.stdout
    assert (manifest["revision"], manifest["revision_date"]) == ("2", "2026-10-20")
    html = (tmp_path / "project_cost_traces.html").read_text()
    assert "<td>2</td><td>2026-10-20</td>" in html
    assert (tmp_path / "project_cost_events.csv").read_text().startswith("event_id,")
    rejected = subprocess.run(
        command[:-1] + [str(CURATED / "outputs")],
        capture_output=True,
        text=True,
        env=env,
    )
    assert rejected.returncode != 0
    assert "outside the curated input" in rejected.stderr
    assert not (CURATED / "outputs").exists()


@pytest.mark.parametrize(
    "basis",
    ["point", "range", "band", "backlog", "combined", "lease_contract", "midstream"],
)
def test_all_award_value_bases_remain_distinct(basis):
    """Synthetic one-sided 10-unit observation; no missing upper bound is filled."""
    row = dict(
        PROJECT="Example development",
        AWARD_YEAR="2020",
        CONTRACTOR="Supplier",
        ASSET_CLASS="surf",
        SCOPE_DESC="Package",
        VALUE_LOW_MM="10",
        VALUE_HIGH_MM="",
        VALUE_BASIS=basis,
        CURRENCY="EUR",
    )
    event = build_portfolio_trace(
        tables=_tables(**{"contract_awards.csv": [row]})
    ).events[0]
    assert event.value_basis == basis
    assert event.high_value == ""
    assert event.currency == "EUR"


def test_unequal_point_award_bounds_are_not_qualified():
    """A point denotes one amount; hand inputs 10 and 20 cannot be one point."""
    row = dict(
        PROJECT="Example development",
        AWARD_YEAR="2020",
        CONTRACTOR="Supplier",
        ASSET_CLASS="surf",
        SCOPE_DESC="Package",
        VALUE_LOW_MM="10",
        VALUE_HIGH_MM="20",
        VALUE_BASIS="point",
    )
    event = build_portfolio_trace(
        tables=_tables(**{"contract_awards.csv": [row]})
    ).events[0]
    assert event.bound_qualification == "NOT_EVALUATED"
    assert (event.low_value, event.high_value) == ("10", "20")


def test_malformed_url_is_displayed_without_an_active_link():
    result = _build([_trail(SOURCE_URL="https://[malformed")])
    assert "<a href=" not in render_trace_html(result)


def test_award_link_source_locator_must_match_the_observation(tmp_path):
    """A link to another award cannot authenticate this observation."""
    import shutil

    root = tmp_path / "curated"
    shutil.copytree(CURATED, root)
    path = root / "award_asset_links.csv"
    with path.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    rows[0]["SOURCE_LOCATOR"] = rows[1]["SOURCE_LOCATOR"]
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="source locator"):
        build_portfolio_trace(root)


@pytest.mark.parametrize(
    "basis,low,high,expected",
    [
        ("point", "10", "10", "structured_award_bounds"),
        ("range", "10", "20", "structured_award_bounds"),
        ("band", "10", "20", "structured_award_bounds"),
        ("not_public", "", "", "NOT_EVALUATED"),
        ("lease_contract", "10", "20", "NOT_EVALUATED"),
        ("midstream", "10", "20", "NOT_EVALUATED"),
        ("combined", "10", "20", "NOT_EVALUATED"),
        ("backlog", "10", "20", "NOT_EVALUATED"),
        ("lease_contract", "10", "10", "NOT_EVALUATED"),
        ("midstream", "10", "10", "NOT_EVALUATED"),
        ("combined", "10", "10", "NOT_EVALUATED"),
        ("backlog", "10", "10", "NOT_EVALUATED"),
        ("range", "10", "", "NOT_EVALUATED"),
        ("range", "", "20", "NOT_EVALUATED"),
        ("range", "", "", "NOT_EVALUATED"),
        ("band", "10", "", "NOT_EVALUATED"),
        ("band", "", "20", "NOT_EVALUATED"),
        ("band", "", "", "NOT_EVALUATED"),
        ("point", "10", "", "NOT_EVALUATED"),
        ("point", "", "20", "NOT_EVALUATED"),
        ("point", "", "", "NOT_EVALUATED"),
    ],
)
def test_award_bound_qualification_requires_comparable_complete_bounds(
    basis, low, high, expected
):
    """Only complete bands/ranges and equal points qualify; no totals are implied."""
    row = dict(
        PROJECT="Example development",
        AWARD_YEAR="2020",
        CONTRACTOR="Supplier",
        ASSET_CLASS="surf",
        SCOPE_DESC="Package",
        VALUE_LOW_MM=low,
        VALUE_HIGH_MM=high,
        VALUE_BASIS=basis,
    )
    event = build_portfolio_trace(
        tables=_tables(**{"contract_awards.csv": [row]})
    ).events[0]
    assert event.bound_qualification == expected
    if expected == "NOT_EVALUATED":
        assert event.bound_qualification_reason
    assert (event.low_value, event.high_value) == (low, high)


@pytest.mark.parametrize(
    "name",
    [
        "project_cost_events.json",
        "project_cost_events.csv",
        "project_cost_traces.html",
        "project_trace_manifest.json",
    ],
)
def test_library_output_collision_preserves_existing_files(tmp_path, name):
    """Any occupied output name must reject the build before any output is written."""
    existing = tmp_path / name
    existing.write_bytes(b"retained evidence")
    with pytest.raises(FileExistsError):
        write_trace_outputs(_build([_trail()]), tmp_path)
    assert existing.read_bytes() == b"retained evidence"
    assert list(tmp_path.iterdir()) == [existing]


@pytest.mark.parametrize("target_exists", [False, True])
@pytest.mark.parametrize(
    "name",
    [
        "project_cost_events.json",
        "project_cost_events.csv",
        "project_cost_traces.html",
        "project_trace_manifest.json",
    ],
)
def test_library_output_symlink_collision_preserves_target(
    tmp_path, name, target_exists
):
    """Occupied names include dangling links; their targets must remain untouched."""
    target = tmp_path / "retained-evidence"
    if target_exists:
        target.write_bytes(b"retained evidence")
    output = tmp_path / "outputs"
    output.mkdir()
    existing = output / name
    existing.symlink_to(target)
    with pytest.raises(FileExistsError):
        write_trace_outputs(_build([_trail()]), output)
    assert existing.is_symlink()
    assert list(output.iterdir()) == [existing]
    if target_exists:
        assert target.read_bytes() == b"retained evidence"
    else:
        assert not target.exists()


def test_revision_metadata_is_supplied_and_retained_in_manifest(tmp_path):
    result = _build([_trail()])
    paths = write_trace_outputs(
        result, tmp_path, revision="2 <draft>", revision_date="2026-10-20"
    )
    html = (tmp_path / "project_cost_traces.html").read_text()
    assert "<td>2 &lt;draft&gt;</td><td>2026-10-20</td>" in html
    manifest = json.loads(paths[-1].read_text())
    assert manifest["revision"] == "2 <draft>"
    assert manifest["revision_date"] == "2026-10-20"
    assert "2026-10-19" not in render_trace_html(result)
