"""Configuration defects must remain distinct from source-data defects."""

import json
from pathlib import Path

import pytest

from worldenergydata.bsee.analysis import drilling_refresh as refresh


@pytest.mark.parametrize(
    "bounds",
    [
        {"date_min": "invalid"},
        {"date_max": None},
        {"date_min": "2021-01-01", "date_max": "2020-01-01"},
    ],
)
def test_invalid_bounds_fail_even_without_source_rows(bounds):
    config = json.loads(
        Path("config/analysis/bsee/drilling_refresh.json").read_text(encoding="utf-8")
    )
    config["tables"]["war"].update(bounds)
    with pytest.raises(refresh.QualityError, match="configuration.*date"):
        refresh._table_qa([], config["tables"]["war"], "day")
    tables = {name: [] for name in config["tables"]}
    with pytest.raises(refresh.QualityError, match="configuration.*date"):
        refresh._defect_records(tables, config, set(), {})


def test_bound_endpoints_are_inclusive():
    spec = {
        "keys": ["SN_WAR"],
        "required": [],
        "dates": ["WAR_START_DT", "WAR_END_DT"],
        "min_rows": 1,
        "unit": "day",
        "date_min": "2020-01-01",
        "date_max": "2020-01-07",
    }
    rows = [{"SN_WAR": "1", "WAR_START_DT": "01/01/2020", "WAR_END_DT": "01/07/2020"}]
    assert refresh._table_qa(rows, spec, "day")["checks"]["out_of_range_dates"] == 0


@pytest.mark.parametrize(
    "identifiers, expected", [(["10", "2"], "2"), (["-3", "-2"], "-3")]
)
def test_quality_example_uses_numeric_identifier_order(monkeypatch, identifiers, expected):
    class Output:
        def __truediv__(self, name):
            return self

        def write_text(self, *args, **kwargs):
            pass

    monkeypatch.setattr(refresh, "_json", lambda *args: None)
    monkeypatch.setattr(refresh, "_csv", lambda *args: None)
    defects = {"unattributed_reports": identifiers}
    result = refresh.write_data_quality(Output(), defects, defects, synthetic=True)
    assert result["rows"][0]["example_id"] == expected
