"""Dated Big Foot cost-trace contract tests."""

import csv
import shutil
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from worldenergydata.cost.timeseries.cost_map_schema import Evidence, MoneyInterval


def _event(**changes):
    from worldenergydata.cost.timeseries.project_trace import CostEvent, DateInterval

    values = {
        "event_id": "evt-test",
        "event_type": "sanction_estimate",
        "lane": "total",
        "project_id": "prj-000001",
        "award_id": None,
        "requirement_id": None,
        "effective_date": DateInterval.from_text("2010"),
        "source_available_date": None,
        "money": MoneyInterval(
            currency="USD",
            price_basis="nominal",
            basis_year=2010,
            ownership_basis="gross",
            scope_basis="project",
            capex_basis="project_capex",
            value_basis="point",
            bound_type="point",
            low_value="4000",
            high_value="4000",
            source_precision="USD million",
        ),
        "evidence": Evidence(
            derivation="disclosed",
            source_provenance="operator",
            source_url="https://example.com/source",
            source_locator="row=1",
            confidence="high",
        ),
        "source_title": "Example source",
        "validation_group_id": "vg-test",
    }
    values.update(changes)
    return CostEvent(**values)


def _copy_curated(tmp_path: Path) -> Path:
    source = Path("data/modules/cost/curated")
    target = tmp_path / "curated"
    target.parent.mkdir(parents=True)
    shutil.copytree(source, target)
    return target


def _rewrite(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


def test_trace_retains_original_date_precision() -> None:
    from worldenergydata.cost.timeseries.project_trace import DateInterval

    annual = DateInterval.from_text("2010")
    monthly = DateInterval.from_text("2015-05")

    assert (annual.start, annual.end, annual.precision) == (
        date(2010, 1, 1),
        date(2010, 12, 31),
        "year",
    )
    assert (monthly.start, monthly.end, monthly.precision) == (
        date(2015, 5, 1),
        date(2015, 5, 31),
        "month",
    )
    with pytest.raises(ValueError, match="bounds must match stated precision"):
        DateInterval(start=date(2010, 2, 1), end=date(2010, 2, 1), precision="year")


def test_effective_date_and_source_availability_are_independent() -> None:
    from worldenergydata.cost.timeseries.project_trace import DateInterval

    event = _event(
        effective_date=DateInterval.from_text("2010"),
        source_available_date=DateInterval.from_text("2011-02-03"),
    )

    assert event.effective_date.precision == "year"
    assert event.source_available_date.start == date(2011, 2, 3)


def test_unknown_source_availability_is_ineligible_for_historical_features() -> None:
    from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

    assert _event(source_available_date=None).historical_feature_eligible is False
    assert all(
        event.source_available_date is None
        and event.historical_feature_eligible is False
        for event in build_big_foot_trace()
    )


def test_events_order_deterministically_at_mixed_precision() -> None:
    from worldenergydata.cost.timeseries.project_trace import DateInterval, order_events

    annual = _event(
        event_id="evt-annual", effective_date=DateInterval.from_text("2010")
    )
    monthly = _event(
        event_id="evt-monthly", effective_date=DateInterval.from_text("2009-12")
    )

    assert [event.event_id for event in order_events((annual, monthly))] == [
        "evt-monthly",
        "evt-annual",
    ]


def test_not_public_event_remains_visible_with_no_value() -> None:
    from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

    event = {row.event_id: row for row in build_big_foot_trace()}["evt-000005"]

    assert event.event_type == "revision_unavailable"
    assert event.effective_date.precision == "month"
    assert event.money is None
    assert event.evidence.derivation == "todo"
    assert event.evidence.source_locator == "sanctioned_projects.csv:PROJECT=Big Foot"


def test_award_event_links_to_approved_asset_identity() -> None:
    from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

    event = {row.event_id: row for row in build_big_foot_trace()}["evt-000001"]

    assert (event.award_id, event.requirement_id) == ("awd-000001", "req-000005")


def test_component_award_is_not_treated_as_cumulative_project_spend() -> None:
    from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

    event = {row.event_id: row for row in build_big_foot_trace()}["evt-000001"]

    assert (event.event_type, event.lane) == ("award", "component")
    assert event.money.low_value == Decimal("45")


def test_trade_press_outturn_retains_low_confidence() -> None:
    from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

    event = {row.event_id: row for row in build_big_foot_trace()}["evt-000004"]

    assert (event.evidence.source_provenance, event.evidence.confidence) == (
        "trade_press",
        "low",
    )
    assert event.money.low_value == Decimal("5100")


def test_missing_years_are_not_interpolated() -> None:
    from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

    assert [event.effective_date.label for event in build_big_foot_trace()] == [
        "2009",
        "2010",
        "2011",
        "2015-05",
        "2018",
    ]


def test_big_foot_trace_has_no_invented_2015_monetary_event() -> None:
    from worldenergydata.cost.timeseries.project_trace import (
        build_big_foot_trace,
        monetary_events,
    )

    assert all(
        event.effective_date.start.year != 2015
        for event in monetary_events(build_big_foot_trace())
    )


def test_big_foot_trace_preserves_component_and_total_lanes() -> None:
    from worldenergydata.cost.timeseries.project_trace import (
        build_big_foot_trace,
        group_events_by_lane,
    )

    lanes = group_events_by_lane(build_big_foot_trace())

    assert [event.event_id for event in lanes["component"]] == [
        "evt-000002",
        "evt-000001",
    ]
    assert [event.event_id for event in lanes["total"]] == [
        "evt-000003",
        "evt-000005",
        "evt-000004",
    ]
    enbridge, ge = lanes["component"]
    assert (enbridge.award_id, enbridge.requirement_id) == ("awd-000002", "req-000006")
    assert enbridge.money.low_value == Decimal("200")
    assert enbridge.money.capex_basis == "non_capex"
    assert ge.money.value_basis == "point"
    assert [event.money.low_value for event in lanes["total"] if event.money] == [
        Decimal("4000"),
        Decimal("5100"),
    ]


def test_trace_rejects_conflicting_duplicate_identity_or_broken_foreign_key(
    tmp_path: Path,
) -> None:
    from worldenergydata.cost.timeseries.project_trace import build_big_foot_trace

    duplicate_root = _copy_curated(tmp_path / "duplicate")
    identity_path = duplicate_root / "cost_event_identity.csv"
    identities = list(csv.DictReader(identity_path.open(encoding="utf-8")))
    conflict = {**identities[1], "OPAQUE_ID": identities[0]["OPAQUE_ID"]}
    _rewrite(identity_path, [*identities, conflict])
    with pytest.raises(ValueError, match="conflicting duplicate event identity"):
        build_big_foot_trace(duplicate_root)

    broken_root = _copy_curated(tmp_path / "broken")
    link_path = broken_root / "award_asset_links.csv"
    links = list(csv.DictReader(link_path.open(encoding="utf-8")))
    links[0]["REQUIREMENT_IDS"] = "req-missing"
    _rewrite(link_path, links)
    with pytest.raises(ValueError, match="broken requirement foreign key"):
        build_big_foot_trace(broken_root)
