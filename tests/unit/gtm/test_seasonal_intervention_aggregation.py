"""Hand-counted synthetic examples for the descriptive seasonal aggregation.

Calendar basis: reports/gtm/seasonal_intervention_risk_windows.py,
ASSUMPTIONS['atlantic_hurricane_season'] declares June-November as season
and August-October as peak. SEASON_OF_MONTH declares meteorological seasons.
These declarations are tested as existing calendar assumptions, not risk evidence.

Independent ledger for SYNTHETIC_RECORDS below (counts are not measured WAR
activity; years and source counters are also synthetic):

Month       Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec | Total
Count         3   0   1   0   3   2   1   2   1   2   3   2 | 20
DRL           2   0   0   0   1   1   0   1   0   1   1   1 |  8
WO            0   0   1   0   2   0   1   1   0   1   1   1 |  8
(blank)       1   0   0   0   0   1   0   0   1   0   1   0 |  4

Each monthly share is its Count / 20. Season = 2+1+2+1+2+3 = 11;
peak = 2+1+2 = 5; off season = 3+0+1+0+3+2 = 9. Shares are 11/20,
5/20 and 9/20 respectively. Each year contributes 10 records. Winter =
3+0+2 = 5; spring = 1+0+3 = 4; summer = 2+1+2 = 5; fall = 1+2+3 = 6.
Activity (in season, off season, total): DRL (4, 4, 8), WO (4, 4, 8),
blank (3, 1, 4). No meanings for the activity tokens are inferred.
Off-season ranks: Jan (3), May (3), Dec (2), Mar (1), Feb (0), Apr (0);
ties use ascending calendar month. Sources a/b have 12/11 synthetic input
rows and 10/10 parseable dates, so only 20 records enter the aggregation.

Empty-input expectations are the same calendar with zero counts/shares and
empty year/activity groups. Neither example supports significance or HSE claims.
"""

import importlib.util
from pathlib import Path
from unittest.mock import Mock

import pytest

REPORT = (
    Path(__file__).resolve().parents[3]
    / "reports/gtm/seasonal_intervention_risk_windows.py"
)

# Listed in reverse year order to test sorted year output independently.
SYNTHETIC_RECORDS = [
    (12, 2024, "DRL", "synthetic_b"),
    (11, 2024, "WO", "synthetic_b"),
    (10, 2024, "WO", "synthetic_b"),
    (9, 2024, "", "synthetic_b"),
    (8, 2024, "DRL", "synthetic_b"),
    (7, 2024, "WO", "synthetic_b"),
    (6, 2024, "DRL", "synthetic_b"),
    (5, 2024, "WO", "synthetic_b"),
    (1, 2024, "", "synthetic_b"),
    (1, 2024, "DRL", "synthetic_b"),
    (12, 2023, "WO", "synthetic_a"),
    (11, 2023, "", "synthetic_a"),
    (11, 2023, "DRL", "synthetic_a"),
    (10, 2023, "DRL", "synthetic_a"),
    (8, 2023, "WO", "synthetic_a"),
    (6, 2023, "", "synthetic_a"),
    (5, 2023, "DRL", "synthetic_a"),
    (5, 2023, "WO", "synthetic_a"),
    (3, 2023, "WO", "synthetic_a"),
    (1, 2023, "DRL", "synthetic_a"),
]
SYNTHETIC_SOURCES = {
    "synthetic_a": {
        "path": "synthetic/a.csv",
        "rows": 12,
        "parseable_dates": 10,
    },
    "synthetic_b": {
        "path": "synthetic/b.csv",
        "rows": 11,
        "parseable_dates": 10,
    },
}


@pytest.fixture
def report():
    """Import definitions by file; the guarded report entry point is not run."""
    spec = importlib.util.spec_from_file_location("seasonal_aggregation", REPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _compute_with_records(report, monkeypatch, records, sources):
    """Replace all data loading before compute; no report renderer is called."""
    loader = Mock(return_value=(records, sources))
    monkeypatch.setattr(report, "load_records", loader)
    payload = report.compute()
    loader.assert_called_once_with()
    return payload


@pytest.fixture
def sample_payload(report, monkeypatch):
    return _compute_with_records(
        report, monkeypatch, SYNTHETIC_RECORDS, SYNTHETIC_SOURCES
    )


def test_monthly_counts_and_shares_reconcile(sample_payload):
    data = sample_payload["data"]
    expected_counts = [3, 0, 1, 0, 3, 2, 1, 2, 1, 2, 3, 2]
    assert data["total_records"] == 20
    assert data["by_month"] == {
        str(month): count for month, count in enumerate(expected_counts, start=1)
    }
    months = data["months"]
    assert [row["month"] for row in months] == list(range(1, 13))
    assert [row["label"] for row in months] == [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ]
    assert [row["count"] for row in months] == expected_counts
    assert [row["share"] for row in months] == pytest.approx(
        [count / 20 for count in expected_counts]
    )
    assert sum(data["by_month"].values()) == 20
    assert sum(row["share"] for row in months) == pytest.approx(1)


def test_season_boundaries_and_peak_shares(sample_payload):
    overlay = sample_payload["overlay"]
    assert overlay["hurricane_season_months"] == [6, 7, 8, 9, 10, 11]
    assert overlay["hurricane_peak_months"] == [8, 9, 10]
    months = sample_payload["data"]["months"]
    assert [row["in_hurricane_season"] for row in months] == [
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
    ]
    assert [row["is_peak"] for row in months] == [
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        True,
        True,
        True,
        False,
        False,
    ]
    assert overlay["records_in_hurricane_season"] == 11
    assert overlay["records_in_peak"] == 5
    assert overlay["records_off_season"] == 9
    assert overlay["share_in_hurricane_season"] == pytest.approx(11 / 20)
    assert overlay["share_in_peak"] == pytest.approx(5 / 20)
    assert overlay["share_off_season"] == pytest.approx(9 / 20)
    assert (
        overlay["records_in_hurricane_season"] + overlay["records_off_season"]
        == sample_payload["data"]["total_records"]
    )


def test_year_and_meteorological_season_totals(sample_payload):
    data = sample_payload["data"]
    assert data["years_present"] == [2023, 2024]
    assert list(data["by_year"].items()) == [("2023", 10), ("2024", 10)]
    assert data["by_season"] == {"Winter": 5, "Spring": 4, "Summer": 5, "Fall": 6}
    assert sum(data["by_year"].values()) == 20
    assert sum(data["by_season"].values()) == 20


def test_each_activity_season_split_reconciles(sample_payload):
    data = sample_payload["data"]
    assert data["by_activity"] == {"DRL": 8, "WO": 8, "(blank)": 4}
    splits = data["activity_season_split"]
    assert splits == {
        "DRL": {"in_season": 4, "off_season": 4, "total": 8},
        "WO": {"in_season": 4, "off_season": 4, "total": 8},
        "(blank)": {"in_season": 3, "off_season": 1, "total": 4},
    }
    for activity, split in splits.items():
        assert split["in_season"] + split["off_season"] == split["total"]
        assert split["total"] == data["by_activity"][activity]
    assert sum(split["in_season"] for split in splits.values()) == 11
    assert sum(split["off_season"] for split in splits.values()) == 9
    assert sum(data["by_activity"].values()) == 20


@pytest.mark.parametrize("reverse_records", [False, True])
def test_off_season_ranking_breaks_ties_by_calendar_month(
    report, monkeypatch, reverse_records
):
    records = SYNTHETIC_RECORDS[::-1] if reverse_records else SYNTHETIC_RECORDS
    payload = _compute_with_records(report, monkeypatch, records, SYNTHETIC_SOURCES)
    assert payload["overlay"]["lower_risk_windows_ranked"] == [
        {"month": "Jan", "count": 3},
        {"month": "May", "count": 3},
        {"month": "Dec", "count": 2},
        {"month": "Mar", "count": 1},
        {"month": "Feb", "count": 0},
        {"month": "Apr", "count": 0},
    ]


def test_source_counters_do_not_replace_record_totals(sample_payload):
    assert sample_payload["data_sources"] == SYNTHETIC_SOURCES
    assert sample_payload["data"]["total_records"] == 20
    assert sample_payload["meta"]["descriptive_only"] is True
    assert sample_payload["meta"]["statistical_significance_claimed"] is False


@pytest.mark.parametrize(
    "sources",
    [
        {},
        {
            "synthetic_empty": {
                "path": "synthetic/empty.csv",
                "rows": 0,
                "parseable_dates": 0,
            }
        },
    ],
    ids=["no-sources", "empty-source"],
)
def test_empty_records_are_an_empty_descriptive_sample(report, monkeypatch, sources):
    payload = _compute_with_records(report, monkeypatch, [], sources)
    data = payload["data"]
    assert payload["data_sources"] == sources
    assert data["total_records"] == 0
    assert data["years_present"] == []
    assert data["by_year"] == {}
    assert data["by_activity"] == {}
    assert data["activity_season_split"] == {}
    assert data["by_month"] == {str(month): 0 for month in range(1, 13)}
    assert data["by_season"] == {"Winter": 0, "Spring": 0, "Summer": 0, "Fall": 0}
    assert [row["month"] for row in data["months"]] == list(range(1, 13))
    assert [row["count"] for row in data["months"]] == [0] * 12
    assert [row["share"] for row in data["months"]] == pytest.approx([0] * 12)
    overlay = payload["overlay"]
    assert overlay["records_in_hurricane_season"] == 0
    assert overlay["records_in_peak"] == 0
    assert overlay["records_off_season"] == 0
    assert overlay["share_in_hurricane_season"] == pytest.approx(0)
    assert overlay["share_in_peak"] == pytest.approx(0)
    assert overlay["share_off_season"] == pytest.approx(0)
    assert overlay["lower_risk_windows_ranked"] == [
        {"month": label, "count": 0}
        for label in ["Jan", "Feb", "Mar", "Apr", "May", "Dec"]
    ]
    assert payload["meta"]["descriptive_only"] is True
    assert payload["meta"]["statistical_significance_claimed"] is False
