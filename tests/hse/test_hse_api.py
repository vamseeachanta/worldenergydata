# ABOUTME: TDD for the HSE query API on the TypedQuery base (wed#363 / workspace-hub#3286).
# ABOUTME: incidents/penalties/statistics/epa_tri query surfaces + wed.hse_api lazy wiring.

"""Tests for ``worldenergydata.hse.api`` (offline synthetic fallback)."""

from __future__ import annotations

import pandas as pd
import pytest

from worldenergydata.common.query_api import TypedQuery


def test_hse_queries_are_typed_query_subclasses():
    from worldenergydata.hse.api import (
        EpaTriQuery,
        IncidentsQuery,
        PenaltiesQuery,
        StatisticsQuery,
    )

    for cls in (IncidentsQuery, PenaltiesQuery, StatisticsQuery, EpaTriQuery):
        assert issubclass(cls, TypedQuery)


def test_hse_incidents_query_returns_typed_df():
    from worldenergydata.hse.api import IncidentsQuery

    df = IncidentsQuery().query(operator="Shell")
    assert isinstance(df, pd.DataFrame)
    for col in ("bsee_incident_id", "operator", "incident_type", "severity"):
        assert col in df.columns
    assert (df["operator"] == "Shell").all()
    assert len(df) == 2  # two synthetic Shell rows


def test_hse_incidents_year_and_severity_filters():
    from worldenergydata.hse.api import IncidentsQuery

    iq = IncidentsQuery()
    df = iq.query(year=2022, severity="fatality")
    assert len(df) == 1
    assert df.iloc[0]["bsee_incident_id"] == "INC-2022-002"


def test_hse_penalties_min_amount():
    from worldenergydata.hse.api import PenaltiesQuery

    df = PenaltiesQuery().query(min_amount=10000)
    assert isinstance(df, pd.DataFrame)
    assert (df["penalty_amount"] >= 10000).all()
    assert len(df) == 2  # 15000 + 50000 (5000 excluded)


def test_hse_statistics_query_grouping():
    from worldenergydata.hse.api import StatisticsQuery

    grouped = StatisticsQuery().query(year=2022, grouping="operator")
    assert isinstance(grouped, pd.DataFrame)
    assert "operator" in grouped.columns
    assert "total_incidents" in grouped.columns
    assert set(grouped["operator"]) == {"Shell", "BP"}


def test_hse_epa_tri_query():
    from worldenergydata.hse.api import EpaTriQuery

    df = EpaTriQuery().query(naics="324110", chemical_carcinogen=True)
    assert isinstance(df, pd.DataFrame)
    assert (df["naics_code"] == "324110").all()
    assert len(df) == 1


def test_hse_api_lazy_attr():
    """wed.hse_api.incidents resolves via __getattr__ (AttributeError pre-change)."""
    import worldenergydata as wed

    api = wed.hse_api
    assert hasattr(api, "incidents")
    assert hasattr(api, "penalties")
    assert hasattr(api, "statistics")
    assert hasattr(api, "epa_tri")
    assert callable(api.incidents.query)


def test_hse_query_envelope():
    from worldenergydata.hse.api import IncidentsQuery

    env = IncidentsQuery().query_envelope(operator="Shell")
    assert env.workflow_id == "hse.incidents"
    assert env.status == "ok"
    assert env.result["records"] == 2
    assert env.determinism["result_hash"] is not None
    assert env.provenance["code_version"]["package_version"] is not None
