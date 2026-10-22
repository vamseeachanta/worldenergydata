"""Synthetic WAR fixtures for abandonment milestones; no pricing assumptions.

Display labels follow bsee/analysis/data/war_activity_codes.yml, codes PA/TA.
That registry records their use in WAR as inferred from borehole status, not
as published WAR definitions. Dates and identifiers below are synthetic.
"""

import pandas as pd
import pytest

from worldenergydata.lower_tertiary import ops_timeline


def _war_tables(monkeypatch, records):
    """Supply in-memory WAR tables without reading the binary inventory."""
    main = pd.DataFrame(
        records,
        columns=[
            "SN_WAR",
            "SURF_LEASE_NUM",
            "API_WELL_NUMBER",
            "WELL_NAME",
            "WAR_START_DT",
            "WELL_ACTIVITY_CD",
        ],
    )
    prop = main[["SN_WAR", "WELL_ACTIVITY_CD"]].copy()
    main = main.drop(columns="WELL_ACTIVITY_CD")
    tables = {"mv_war_main.bin": main, "mv_war_main_prop.bin": prop}
    monkeypatch.setattr(ops_timeline, "_read_war_bin", tables.__getitem__)
    return tables


@pytest.mark.parametrize(
    ("code", "label"),
    [("PA", "Plug & abandon"), ("TA", "Temporary abandonment")],
)
@pytest.mark.parametrize("name", [None, pd.NA, "", "  "])
def test_abandonment_without_well_name_is_retained(monkeypatch, code, label, name):
    """Hand calculation: one valid dated row gives one milestone at that date.

    The missing display name cannot remove the known API or change its date.
    Expected labels are the legacy display strings in the registry cited above.
    """
    _war_tables(
        monkeypatch,
        [(1, "G00001", "11111111111100", name, "2024-01-05", code)],
    )

    result = ops_timeline.derive_war_operations("G00001", "2024-01-31")

    assert result.to_dict("records") == [
        {
            "API_WELL_NUMBER": "11111111111100",
            "date": pd.Timestamp("2024-01-05"),
            "operation": label,
            "detail": "API 11111111111100",
        }
    ]


def test_abandonment_keeps_earliest_valid_date_and_existing_operations(monkeypatch):
    """Hand enumeration: retain COM Jan 1, TA Jan 5, WO Jan 20, PA Jan 25.

    Later duplicate TA rows collapse to Jan 5 after trimming names/codes.
    Invalid/future dates, other leases, drilling and unknown codes contribute
    no events. PA is retained on the inclusive cutoff. No durations are inferred.
    """
    tables = _war_tables(
        monkeypatch,
        [
            (1, ' "g 00001" ', "11111111111100", " Well A ", "2024-01-12", "ta"),
            (2, "G00001", "11111111111100", "Well A", "2024-01-05", " TA "),
            (3, "G00001", "11111111111100", "Well A", "2024-01-25", "PA"),
            (4, "G00001", "11111111111100", "Well A", "2024-01-01", "COM"),
            (5, "G00001", "11111111111100", "Well A", "2024-01-20", "WO"),
            (6, "G00002", "22222222222200", "Well B", "2024-01-02", "PA"),
            (7, "G00001", "11111111111100", "Well A", "2024-02-01", "PA"),
            (8, "G00001", "11111111111100", "Well A", "invalid", "PA"),
            (9, "G00001", "11111111111100", "Well A", "2023-12-01", "DRL"),
            (10, "G00001", "11111111111100", "Well A", "2023-12-02", "UNKNOWN"),
        ],
    )
    original = {name: table.copy(deep=True) for name, table in tables.items()}

    result = ops_timeline.derive_war_operations("g00001", "2024-01-25")

    assert list(zip(result["date"].dt.strftime("%Y-%m-%d"), result["operation"])) == [
        ("2024-01-01", "Completion"),
        ("2024-01-05", "Temporary abandonment"),
        ("2024-01-20", "Workover"),
        ("2024-01-25", "Plug & abandon"),
    ]
    assert result["detail"].tolist() == ["Well A (11111111111100)"] * 4
    for name in tables:
        pd.testing.assert_frame_equal(tables[name], original[name])


def test_abandonment_survives_timeline_assembly(monkeypatch):
    """Hand enumeration: two APIs give two PA events, despite a shared name/date.

    Repeating the lease contributes no additional events. Both dates belong to
    the January month bucket. The real WAR derivation is exercised by assembly.
    """
    _war_tables(
        monkeypatch,
        [
            (1, "G00001", "11111111111100", "Well", "2024-01-05", "PA"),
            (2, "G00001", "22222222222200", "Well", "2024-01-05", "PA"),
        ],
    )
    empty = pd.DataFrame(columns=["API_WELL_NUMBER", "date", "operation", "detail"])
    monkeypatch.setattr(
        ops_timeline, "derive_first_production_dates", lambda *_: empty.copy()
    )

    result = ops_timeline.build_operations_timeline(["G00001", "G00001"], "2024-01-31")

    assert result["API_WELL_NUMBER"].tolist() == ["11111111111100", "22222222222200"]
    assert result["operation"].tolist() == ["Plug & abandon", "Plug & abandon"]
    assert result["month"].tolist() == [pd.Timestamp("2024-01-01")] * 2


def test_unmatched_lease_returns_empty_operation_schema(monkeypatch):
    """Hand enumeration: no matching lease gives zero milestones."""
    _war_tables(
        monkeypatch,
        [(1, "G00002", "11111111111100", None, "2024-01-05", "PA")],
    )

    result = ops_timeline.derive_war_operations("G00001", "2024-01-31")

    assert result.empty
    assert result.columns.tolist() == ["API_WELL_NUMBER", "date", "operation", "detail"]
