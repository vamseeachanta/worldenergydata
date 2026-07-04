# ABOUTME: HSE query API on the shared TypedQuery base (wed#363 / workspace-hub#3286).
# ABOUTME: incidents/penalties/statistics/epa_tri query surfaces with an offline synthetic fallback.

"""HSE (Health, Safety, Environment) query API.

Parity with ``marine_safety.api`` built on the shared
:class:`~worldenergydata.common.query_api.TypedQuery` base (workspace-hub#3286).
Closes the *query-surface* portion of wed#363: ``incidents`` (HSEIncident),
``penalties`` (ViolationIncident), ``statistics`` (SafetyStatistic) and
``epa_tri`` (ToxicRelease).

Each surface queries a SQLAlchemy session. When no session is injected and no
populated DB is available, it falls back to an in-memory SQLite database seeded
with a small synthetic sample -- mirroring marine_safety's synthetic default so
the query surface is testable offline (no live DB, no ``/mnt/ace``). The live
DB / async-pooling / CLI / notebook ACs of wed#363 remain gated on wed#359 +
HSE DB population and stay open under #363.

Usage::

    import worldenergydata as wed

    df = wed.hse_api.incidents.query(operator="Shell", year=2022, severity="fatality")
    df = wed.hse_api.penalties.query(min_amount=10000)
    df = wed.hse_api.statistics.query(year=2022, grouping="operator")
    df = wed.hse_api.epa_tri.query(naics="324110")
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from worldenergydata.common.query_api import FilterSpec, TypedQuery


# ---------------------------------------------------------------------------
# Offline synthetic session (mirrors marine_safety's synthetic default)
# ---------------------------------------------------------------------------
def build_synthetic_session():
    """Return a SQLAlchemy session over an in-memory SQLite DB seeded with a
    small, deterministic synthetic HSE sample. Used as the offline default."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from worldenergydata.hse.database.models import (
        Base,
        HSEIncident,
        SafetyStatistic,
        ToxicRelease,
        ViolationIncident,
    )

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()

    incidents = [
        HSEIncident(
            bsee_incident_id="INC-2021-001",
            incident_date=datetime(2021, 3, 1),
            operator="Shell",
            field_name="Mars",
            incident_type="injury",
            severity="lost_time",
            latitude=28.0,
            longitude=-90.0,
            description="hand laceration",
        ),
        HSEIncident(
            bsee_incident_id="INC-2022-002",
            incident_date=datetime(2022, 6, 15),
            operator="Shell",
            field_name="Mars",
            incident_type="equipment_failure",
            severity="fatality",
            latitude=28.1,
            longitude=-90.1,
            description="crane collapse",
        ),
        HSEIncident(
            bsee_incident_id="INC-2022-003",
            incident_date=datetime(2022, 9, 2),
            operator="BP",
            field_name="Thunder Horse",
            incident_type="spill",
            severity="recordable",
            latitude=28.2,
            longitude=-88.5,
            description="oil release",
        ),
    ]
    session.add_all(incidents)
    session.flush()

    penalties = [
        ViolationIncident(
            hse_incident_id=incidents[1].id,
            inc_number="INC-A",
            violation_type="safety",
            regulation_cited="30 CFR 250.188",
            penalty_amount=5000.0,
            penalty_status="proposed",
        ),
        ViolationIncident(
            hse_incident_id=incidents[1].id,
            inc_number="INC-B",
            violation_type="environmental",
            regulation_cited="30 CFR 250.300",
            penalty_amount=15000.0,
            penalty_status="assessed",
        ),
        ViolationIncident(
            hse_incident_id=incidents[2].id,
            inc_number="INC-C",
            violation_type="environmental",
            regulation_cited="30 CFR 250.300",
            penalty_amount=50000.0,
            penalty_status="paid",
        ),
    ]
    session.add_all(penalties)

    statistics = [
        SafetyStatistic(
            report_date=datetime(2022, 12, 31),
            operator="Shell",
            field_name="Mars",
            operational_period=365,
            total_incidents=2,
            fatality_count=1,
            lost_time_count=1,
            recordable_count=0,
            near_miss_count=3,
            minor_count=5,
        ),
        SafetyStatistic(
            report_date=datetime(2022, 12, 31),
            operator="BP",
            field_name="Thunder Horse",
            operational_period=365,
            total_incidents=1,
            fatality_count=0,
            lost_time_count=0,
            recordable_count=1,
            near_miss_count=2,
            minor_count=4,
        ),
    ]
    session.add_all(statistics)

    releases = [
        ToxicRelease(
            tri_facility_id="TRI-1",
            facility_name="Mars Platform",
            city="Gulf",
            state="LA",
            naics_code="324110",
            chemical_name="Benzene",
            cas_number="71-43-2",
            total_releases_pounds=1200.0,
            reporting_year=2022,
        ),
        ToxicRelease(
            tri_facility_id="TRI-2",
            facility_name="Thunder Horse",
            city="Gulf",
            state="LA",
            naics_code="211120",
            chemical_name="Toluene",
            cas_number="108-88-3",
            total_releases_pounds=800.0,
            reporting_year=2021,
        ),
    ]
    session.add_all(releases)
    session.commit()
    return session


class _HSEQuery(TypedQuery):
    """Common machinery: a session (injected or synthetic) + pandas filtering."""

    #: ORM column names emitted into the result DataFrame.
    columns: List[str] = []
    #: Map normalized-filter key -> DataFrame column to filter on (list filters).
    _list_filter_columns: Dict[str, str] = {}
    #: DataFrame column holding the year-bearing date (or int) for year filters.
    _year_column: Optional[str] = None
    _year_is_int: bool = False

    def __init__(self, session: Any = None) -> None:
        self._session = session

    def _get_session(self):
        if self._session is None:
            self._session = build_synthetic_session()
        return self._session

    def _base_frame(self) -> pd.DataFrame:
        """Load this surface's rows into a DataFrame. Subclasses override."""
        raise NotImplementedError

    def _apply_common_filters(
        self, df: pd.DataFrame, normalized: Dict[str, Any]
    ) -> pd.DataFrame:
        for key, col in self._list_filter_columns.items():
            values = normalized.get(key)
            if values and col in df.columns:
                df = df[df[col].isin(values)]
        if self._year_column and self._year_column in df.columns:
            sy = normalized.get("start_year")
            ey = normalized.get("end_year")
            if sy is not None or ey is not None:
                if self._year_is_int:
                    years = pd.to_numeric(df[self._year_column], errors="coerce")
                else:
                    years = pd.to_datetime(df[self._year_column], errors="coerce").dt.year
                if sy is not None:
                    df = df[years >= sy]
                if ey is not None:
                    df = df[years <= ey]
        return df.reset_index(drop=True)

    @staticmethod
    def _rows_to_df(rows, columns: List[str]) -> pd.DataFrame:
        records = [{c: getattr(r, c, None) for c in columns} for r in rows]
        return pd.DataFrame(records, columns=columns)


class IncidentsQuery(_HSEQuery):
    """Query HSE incidents (``HSEIncident``)."""

    query_id = "hse.incidents"
    filters = [
        FilterSpec("operators", "operator", "list"),
        FilterSpec("incident_types", "incident_type", "list"),
        FilterSpec("severities", "severity", "list"),
        FilterSpec("fields", "field", "list"),
        FilterSpec("years", None, "year"),
    ]
    columns = [
        "bsee_incident_id",
        "incident_date",
        "operator",
        "field_name",
        "incident_type",
        "severity",
        "latitude",
        "longitude",
        "description",
    ]
    result_columns = columns
    _list_filter_columns = {
        "operators": "operator",
        "incident_types": "incident_type",
        "severities": "severity",
        "fields": "field_name",
    }
    _year_column = "incident_date"

    def _base_frame(self) -> pd.DataFrame:
        from worldenergydata.hse.database.models import HSEIncident

        rows = self._get_session().query(HSEIncident).all()
        return self._rows_to_df(rows, self.columns)

    def _execute(self, normalized: Dict[str, Any]) -> pd.DataFrame:
        return self._apply_common_filters(self._base_frame(), normalized)


class PenaltiesQuery(_HSEQuery):
    """Query civil penalties (``ViolationIncident`` joined to ``HSEIncident``).

    Supports a ``min_amount`` passthrough filtering ``penalty_amount >= min``.
    """

    query_id = "hse.penalties"
    filters = [
        FilterSpec("operators", "operator", "list"),
        FilterSpec("penalty_statuses", "penalty_status", "list"),
        FilterSpec("years", None, "year"),
    ]
    columns = [
        "inc_number",
        "operator",
        "incident_date",
        "violation_type",
        "regulation_cited",
        "penalty_amount",
        "penalty_status",
    ]
    result_columns = columns
    _list_filter_columns = {
        "operators": "operator",
        "penalty_statuses": "penalty_status",
    }
    _year_column = "incident_date"

    def _base_frame(self) -> pd.DataFrame:
        from worldenergydata.hse.database.models import ViolationIncident

        rows = self._get_session().query(ViolationIncident).all()
        records = []
        for r in rows:
            parent = r.hse_incident
            records.append(
                {
                    "inc_number": r.inc_number,
                    "operator": getattr(parent, "operator", None),
                    "incident_date": getattr(parent, "incident_date", None),
                    "violation_type": r.violation_type,
                    "regulation_cited": r.regulation_cited,
                    "penalty_amount": r.penalty_amount,
                    "penalty_status": r.penalty_status,
                }
            )
        return pd.DataFrame(records, columns=self.columns)

    def _execute(self, normalized: Dict[str, Any]) -> pd.DataFrame:
        df = self._apply_common_filters(self._base_frame(), normalized)
        min_amount = normalized.get("_passthrough", {}).get("min_amount")
        if min_amount is not None and "penalty_amount" in df.columns:
            df = df[df["penalty_amount"].fillna(-1) >= min_amount].reset_index(drop=True)
        return df


class StatisticsQuery(_HSEQuery):
    """Query aggregated safety statistics (``SafetyStatistic``).

    A ``grouping`` passthrough (e.g. ``"operator"`` / ``"field_name"``) groups
    the count columns; a ``metric`` passthrough selects a single count column.
    """

    query_id = "hse.statistics"
    filters = [
        FilterSpec("operators", "operator", "list"),
        FilterSpec("fields", "field", "list"),
        FilterSpec("years", None, "year"),
    ]
    _count_columns = [
        "total_incidents",
        "fatality_count",
        "lost_time_count",
        "recordable_count",
        "near_miss_count",
        "minor_count",
    ]
    columns = ["report_date", "operator", "field_name"] + _count_columns
    result_columns = columns
    _list_filter_columns = {"operators": "operator", "fields": "field_name"}
    _year_column = "report_date"

    def _base_frame(self) -> pd.DataFrame:
        from worldenergydata.hse.database.models import SafetyStatistic

        rows = self._get_session().query(SafetyStatistic).all()
        return self._rows_to_df(rows, self.columns)

    def _execute(self, normalized: Dict[str, Any]) -> pd.DataFrame:
        df = self._apply_common_filters(self._base_frame(), normalized)
        passthrough = normalized.get("_passthrough", {})
        grouping = passthrough.get("grouping")
        metric = passthrough.get("metric")
        value_cols = [metric] if metric in self._count_columns else self._count_columns
        if grouping and grouping in df.columns:
            df = (
                df.groupby(grouping, as_index=False)[value_cols].sum().reset_index(drop=True)
            )
        elif metric in self._count_columns:
            keep = [c for c in ("report_date", "operator", "field_name") if c in df.columns]
            df = df[keep + [metric]].reset_index(drop=True)
        return df


class EpaTriQuery(_HSEQuery):
    """Query EPA TRI toxic-release records (``ToxicRelease``)."""

    query_id = "hse.epa_tri"
    filters = [
        FilterSpec("naics_codes", "naics", "list"),
        FilterSpec("chemicals", "chemical", "list"),
        FilterSpec("states", "state", "list"),
        FilterSpec("years", None, "year"),
    ]
    columns = [
        "tri_facility_id",
        "facility_name",
        "city",
        "state",
        "naics_code",
        "chemical_name",
        "cas_number",
        "total_releases_pounds",
        "reporting_year",
    ]
    result_columns = columns
    _list_filter_columns = {
        "naics_codes": "naics_code",
        "chemicals": "chemical_name",
        "states": "state",
    }
    _year_column = "reporting_year"
    _year_is_int = True

    def _base_frame(self) -> pd.DataFrame:
        from worldenergydata.hse.database.models import ToxicRelease

        rows = self._get_session().query(ToxicRelease).all()
        return self._rows_to_df(rows, self.columns)

    def _execute(self, normalized: Dict[str, Any]) -> pd.DataFrame:
        # `chemical_carcinogen` (passthrough) is accepted but a best-effort no-op
        # offline: the synthetic sample carries no carcinogen flag column.
        return self._apply_common_filters(self._base_frame(), normalized)


# Module-level singletons for convenience attribute access (wed.hse_api.<name>).
incidents = IncidentsQuery()
penalties = PenaltiesQuery()
statistics = StatisticsQuery()
epa_tri = EpaTriQuery()
