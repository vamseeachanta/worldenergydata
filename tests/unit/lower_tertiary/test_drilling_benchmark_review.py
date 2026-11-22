"""Review regressions: calendar/rig separation, committed inputs and UTF-8.

All hand-calculation inputs are synthetic. Saved inputs are read without edits;
generated pages remain in pytest's disposable directory.
"""

import csv
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "scripts"))

from lower_tertiary.drilling_benchmark import benchmark_well, load_benchmark_rows

from tests.unit.lower_tertiary.test_drilling_benchmark import (
    _builder,
    _rows,
    _well,
)

CALENDAR_DAYS = "spud_to_td_calendar_days"


@pytest.fixture
def legacy_text_locale(monkeypatch):
    """Emulate implicit cp1252 while preserving explicitly selected encodings."""
    original_open = Path.open

    def legacy_open(
        path, mode="r", buffering=-1, encoding=None, errors=None, newline=None
    ):
        if "b" not in mode and encoding in (None, "locale"):
            encoding = "cp1252"
        return original_open(path, mode, buffering, encoding, errors, newline)

    monkeypatch.setattr(Path, "open", legacy_open)


def _calendar_rows():
    return [
        {
            **{k: v for k, v in row.items() if k != "drilling_days"},
            CALENDAR_DAYS: row["drilling_days"],
        }
        for row in _rows()
    ]


def _dated_well():
    # Leap-year Jan (31) + Feb (29) = 60 elapsed calendar days, versus 999
    # synthetic rig-days. The legacy rig value must never enter this fit.
    return dict(
        _well(),
        spud_date="2020-01-01",
        td_date="2020-03-01",
        drilling_rig_days=999,
        first_oil="2021-01-01",
        field_id="example",
        slot="A",
    )


def test_committed_calendar_schema_loads_without_relabeling():
    path = REPO / "reports/lower_tertiary/lt_drilling_insights.csv"
    with path.open(encoding="utf-8", newline="") as stream:
        expected = list(csv.DictReader(stream))
    rows = load_benchmark_rows(path)
    assert rows == expected
    assert rows and CALENDAR_DAYS in rows[0]
    assert "drilling_days" not in rows[0]


@pytest.mark.parametrize("rig_days", [999, None, 0])
def test_calendar_fit_uses_dates_without_requiring_rig_days(rig_days):
    well = dict(_dated_well(), drilling_rig_days=rig_days)
    result = benchmark_well(well, _calendar_rows())
    assert result["status"] == "EVALUATED"
    assert result["duration_basis"] == CALENDAR_DAYS
    assert result["peer_count"] == 2
    assert result["fitted_days"] == pytest.approx(30)
    assert result["observed_to_fitted"] == pytest.approx(2)
    assert "calendar" in result["limitation"].lower()
    assert "suspension" in result["limitation"].lower()


@pytest.mark.parametrize(
    "spud,td",
    [
        (None, "2020-03-01"),
        ("2020-01-01", None),
        ("2020-01-01", "bad"),
        ("2020-01-01", "2020-02-30"),
        ("2020-03-01", "2020-01-01"),
        ("2020-01-01", "2020-01-01"),
    ],
)
def test_calendar_fit_never_falls_back_to_rig_days(spud, td):
    well = dict(_dated_well(), spud_date=spud, td_date=td, drilling_rig_days=60)
    result = benchmark_well(well, _calendar_rows())
    assert result["status"] == "NOT_EVALUATED"
    assert "calendar" in result["reason"].lower()
    assert result["observed_to_fitted"] is None


def test_calendar_source_disagreement_is_not_compared():
    rows = _calendar_rows()
    rows[0][CALENDAR_DAYS] = 61
    result = benchmark_well(_dated_well(), rows)
    assert result["status"] == "NOT_EVALUATED"
    assert "disagree" in result["reason"]


@pytest.mark.parametrize("index", [0, 1])
def test_calendar_and_legacy_duration_sources_are_not_mixed(index):
    rows = _calendar_rows()
    rows[index] = _rows()[index]
    result = benchmark_well(_dated_well(), rows)
    assert result["status"] == "NOT_EVALUATED"
    assert "basis" in result["reason"].lower()


def test_calendar_drill_card_names_its_basis_separately_from_rig_days():
    builder = _builder()
    result = builder.facts_to_well(
        _dated_well(), {"display_name": "Example"}, drilling_rows=_calendar_rows()
    )
    card = result["cards"][0]
    assert card["big"] == "999 rig-days"
    assert card["badge"] == "Calendar days vs depth · 2.0× fitted"
    assert "Fitted 30.0 calendar days; 2 other API wellbores" in card["li"]
    assert result["cAxis"]["end"] == 999


@pytest.mark.parametrize("scale,display", [(1, "0.033"), (1000, "3.3e-05")])
def test_small_positive_ratio_remains_visible(scale, display):
    builder = _builder()
    well = dict(_dated_well(), drilling_rig_days=1)
    rows = _rows()
    rows[0]["drilling_days"] = 1
    for row in rows[1:]:
        row["drilling_days"] *= scale
    result = builder.facts_to_well(
        well, {"display_name": "Example"}, drilling_rows=rows
    )
    assert result["drilling_benchmark"]["observed_to_fitted"] == pytest.approx(
        1 / (30 * scale)
    )
    assert result["cards"][0]["badge"] == f"Days vs depth · {display}× fitted"
    assert f"{display}× fitted" in builder.render(result)


@pytest.mark.parametrize("legacy_locale", [False, True])
def test_generator_reads_committed_inputs_and_writes_utf8_pages(
    tmp_path, monkeypatch, legacy_locale, request
):
    builder = _builder()
    inputs = (builder.FACTS, builder.DRILLING_CSV, builder.TEMPLATE)
    before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs}
    facts = json.loads(builder.FACTS.read_text(encoding="utf-8"))
    if legacy_locale:
        request.getfixturevalue("legacy_text_locale")
    we = SimpleNamespace(
        compute_well_economics=lambda *a, **k: SimpleNamespace(to_json=dict),
        norms_comparison=lambda *a: {},
    )
    monkeypatch.setattr(builder, "HERE", tmp_path)
    monkeypatch.setattr(
        builder,
        "_economics_context",
        lambda: (we, {"display": {}}, None, None, {}, {}, None),
    )
    builder.main()
    pages = sorted(tmp_path.glob("*_well.html"))
    assert len(pages) == len(facts["wells"])
    evaluated = 0
    for page in pages:
        text = page.read_text(encoding="utf-8")
        payload, _ = json.JSONDecoder().raw_decode(text.split("const WELL = ", 1)[1])
        result = payload["drilling_benchmark"]
        assert result["duration_basis"] == CALENDAR_DAYS
        assert "calendar" in result["limitation"].lower()
        if result["status"] == "EVALUATED":
            evaluated += 1
            assert payload["cards"][0]["badge"].startswith("Calendar days vs depth")
        else:
            assert result["reason"] in payload["cards"][0]["li"]
            assert result["observed_to_fitted"] is None
    assert evaluated > 0
    assert "Well life-cycle timelines" in (tmp_path / "index.html").read_text(
        encoding="utf-8"
    )
    assert before == {
        path: hashlib.sha256(path.read_bytes()).hexdigest() for path in inputs
    }


def test_template_is_read_as_utf8_with_legacy_locale(
    tmp_path, monkeypatch, legacy_text_locale
):
    builder = _builder()
    template = tmp_path / "template.html"
    template.write_text("<p>Drill → 深</p>__WELL_JSON__", encoding="utf-8")
    monkeypatch.setattr(builder, "TEMPLATE", template)
    assert builder.render({"title": "Synthetic"}) == (
        '<p>Drill → 深</p>{\n  "title": "Synthetic"\n}'
    )
