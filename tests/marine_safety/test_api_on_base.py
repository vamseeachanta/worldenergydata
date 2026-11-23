# ABOUTME: Behavior-preservation regression for marine_safety on the TypedQuery base (#3286).
# ABOUTME: Golden: wed.marine_safety_api.incidents.query(source="maib") -> 50 rows / 10 cols.

"""Regression tests proving the TypedQuery re-expression of
``marine_safety.api.IncidentsQuery`` preserves the pre-refactor behavior."""

from __future__ import annotations

import pandas as pd

from worldenergydata.common.query_api import TypedQuery

GOLDEN_COLUMNS = [
    "source",
    "incident_id",
    "date",
    "incident_type",
    "vessel_type",
    "region",
    "fatalities",
    "injuries",
    "severity",
    "description",
]


def test_incidents_query_is_typed_query_subclass():
    from worldenergydata.marine_safety.api import IncidentsQuery

    assert issubclass(IncidentsQuery, TypedQuery)


def test_marine_safety_query_unchanged():
    """Golden: source="maib" returns 50 rows / 10 documented columns."""
    import worldenergydata as wed

    df = wed.marine_safety_api.incidents.query(source="maib")
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 50
    assert list(df.columns) == GOLDEN_COLUMNS
    assert (df["source"] == "maib").all()


def test_marine_safety_plural_and_year_shorthand():
    from worldenergydata.marine_safety.api import IncidentsQuery

    iq = IncidentsQuery()
    multi = iq.query(sources=["maib", "imo"])
    assert set(multi["source"].unique()).issubset({"maib", "imo"})

    vt = iq.query(vessel_type="tanker")
    if not vt.empty:
        assert (vt["vessel_type"] == "tanker").all()


def test_marine_safety_helpers_unchanged():
    """trends/top_types/correlations/risk_hotspots still delegate + return shapes."""
    from worldenergydata.marine_safety.api import IncidentsQuery

    iq = IncidentsQuery()
    data = iq.query()
    assert not data.empty

    trends = iq.trends(data)
    assert isinstance(trends, pd.DataFrame)
    assert "count" in trends.columns

    top = iq.top_types(data, n=3)
    assert isinstance(top, pd.DataFrame)
    assert len(top) <= 3

    corr = iq.correlations(data)
    assert isinstance(corr, dict)

    hotspots = iq.risk_hotspots(data)
    assert isinstance(hotspots, pd.DataFrame)


def test_marine_safety_query_envelope():
    """The base query_envelope() works on the live marine_safety surface."""
    from worldenergydata.marine_safety.api import IncidentsQuery

    env = IncidentsQuery().query_envelope(source="maib")
    assert env.workflow_id == "marine_safety.incidents"
    assert env.status == "ok"
    assert env.result["records"] == 50
    assert env.result["columns"] == GOLDEN_COLUMNS
    assert env.determinism["result_hash"] is not None
