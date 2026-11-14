# ABOUTME: HSE query API on the shared TypedQuery base (wed#363 / workspace-hub#3286).
# ABOUTME: incidents/penalties/statistics/epa_tri query surfaces with an offline synthetic fallback.

"""Validated HSE query surfaces with pandas results and async database access.

``HSEApi(HSEQueryConfig(database_url=...))`` reads an existing database.
Module singletons retain the offline demonstration for compatibility and label
all frames ``data_kind=synthetic``. No configured query falls back to samples.
See ``docs/modules/hse/query-api.html`` for schema-dependent limitations.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

import pandas as pd
from sqlalchemy import extract, func, select

from worldenergydata.common.query_api import FilterSpec, TypedQuery
from worldenergydata.hse.database.models import (
    HSEIncident,
    SafetyStatistic,
    ToxicRelease,
    ViolationIncident,
)
from worldenergydata.hse.query_config import HSEBackend, HSEQueryConfig, QueryFilters


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
    """SQL selections shared by synchronous and asynchronous query methods."""

    columns: ClassVar[list[str]] = []
    _list_filter_columns: ClassVar[dict] = {}
    _year_column = None
    _year_is_int = False
    extra_filters: ClassVar[set[str]] = set()

    def __init__(self, session=None, *, backend=None):
        if session is not None and backend is not None:
            raise ValueError("Supply a session or a backend, not both")
        self._session = session
        self._backend = backend
        self._synthetic = session is None and backend is None

    def _normalize(self, **kwargs):
        allowed = {"year", "start_year", "end_year", "limit", "offset"}
        for spec in self.filters:
            if spec.kind == "list":
                allowed.update({spec.name, spec.singular} - {None})
                for key in (spec.name,):
                    value = kwargs.get(key)
                    if value is not None and not isinstance(value, list):
                        raise TypeError(f"{key} must be a list")
        unknown = kwargs.keys() - allowed - self.extra_filters
        if unknown:
            raise ValueError(f"Unknown filters: {', '.join(sorted(unknown))}")
        normalized = super()._normalize(**kwargs)
        normalized.update(normalized.pop("_passthrough"))
        result = QueryFilters.model_validate(normalized).model_dump()
        if result["metric"] is not None and result["metric"] not in COUNT_COLUMNS:
            raise ValueError("Unknown safety statistic metric")
        if result["chemical_carcinogen"] is not None:
            raise NotImplementedError(
                "NOT_EVALUATED: ToxicRelease has no carcinogen classification"
            )
        if isinstance(self, OshaQuery) and result["naics_codes"] is not None:
            raise NotImplementedError(
                "NOT_EVALUATED: OSHA NAICS is not a structured incident column"
            )
        return result

    def _statement(self, normalized):
        statement = self._select(normalized)
        for key, column in self._list_filter_columns.items():
            if normalized[key]:
                statement = statement.where(column.in_(normalized[key]))
        year = type(self)._year_column
        if year is not None:
            year = year if self._year_is_int else extract("year", year)
            if normalized["start_year"] is not None:
                statement = statement.where(year >= normalized["start_year"])
            if normalized["end_year"] is not None:
                statement = statement.where(year <= normalized["end_year"])
        if isinstance(self, IncidentsQuery):
            sources = normalized["sources"]
            if isinstance(self, OshaQuery):
                sources = ["osha"]
            if sources and len(set(sources)) == 1:
                is_osha = HSEIncident.bsee_incident_id.startswith(
                    "OSHA-", autoescape=True
                )
                statement = statement.where(
                    is_osha if sources[0] == "osha" else ~is_osha
                )
        if isinstance(self, PenaltiesQuery) and normalized["min_amount"] is not None:
            statement = statement.where(
                ViolationIncident.penalty_amount >= normalized["min_amount"]
            )
        return statement.limit(normalized["limit"]).offset(normalized["offset"])

    def _select(self, normalized):
        return select(*(getattr(self.model, name) for name in self.columns)).order_by(
            self.model.id
        )

    def _frame(self, result, statement):
        frame = pd.DataFrame(
            result.mappings().all(), columns=statement.selected_columns.keys()
        )
        frame.attrs["data_kind"] = "synthetic" if self._synthetic else "database"
        frame.attrs["workflow_id"] = self.query_id
        return frame

    def _execute(self, normalized):
        statement = self._statement(normalized)
        if self._backend is not None:
            with self._backend.session() as session:
                return self._frame(session.execute(statement), statement)
        if self._session is None:
            self._session = build_synthetic_session()
        return self._frame(self._session.execute(statement), statement)

    async def aquery(self, **kwargs) -> pd.DataFrame:
        """Run the same SQL using a pooled async engine and a fresh session."""
        normalized = self._normalize(**kwargs)
        if self._backend is None:
            raise ValueError("Async queries require an explicitly configured HSEApi")
        statement = self._statement(normalized)
        async with self._backend.async_session() as session:
            return self._frame(await session.execute(statement), statement)

    def close(self):
        """Release a demonstration session; injected sessions remain caller-owned."""
        if self._synthetic and self._session is not None:
            engine = self._session.get_bind()
            self._session.close()
            engine.dispose()
            self._session = None


class IncidentsQuery(_HSEQuery):
    """Query incidents; source is inferred from the existing OSHA identifier prefix."""

    query_id = "hse.incidents"
    model = HSEIncident
    filters: ClassVar[list[FilterSpec]] = [
        FilterSpec("operators", "operator", "list"),
        FilterSpec("incident_types", "incident_type", "list"),
        FilterSpec("severities", "severity", "list"),
        FilterSpec("fields", "field", "list"),
        FilterSpec("sources", "source", "list"),
        FilterSpec("years", None, "year"),
    ]
    columns: ClassVar[list[str]] = [
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
    _list_filter_columns: ClassVar[dict] = {
        "operators": HSEIncident.operator,
        "incident_types": HSEIncident.incident_type,
        "severities": HSEIncident.severity,
        "fields": HSEIncident.field_name,
    }
    _year_column = HSEIncident.incident_date


class PenaltiesQuery(_HSEQuery):
    """Select penalties joined to parent incidents; year means incident year."""

    query_id = "hse.penalties"
    filters: ClassVar[list[FilterSpec]] = [
        FilterSpec("operators", "operator", "list"),
        FilterSpec("penalty_statuses", "penalty_status", "list"),
        FilterSpec("years", None, "year"),
    ]
    extra_filters: ClassVar[set[str]] = {"min_amount"}
    columns: ClassVar[list[str]] = [
        "inc_number",
        "operator",
        "incident_date",
        "violation_type",
        "regulation_cited",
        "penalty_amount",
        "penalty_status",
    ]
    result_columns = columns
    _list_filter_columns: ClassVar[dict] = {
        "operators": HSEIncident.operator,
        "penalty_statuses": ViolationIncident.penalty_status,
    }
    _year_column = HSEIncident.incident_date

    def _select(self, normalized):
        return (
            select(
                ViolationIncident.inc_number,
                HSEIncident.operator,
                HSEIncident.incident_date,
                ViolationIncident.violation_type,
                ViolationIncident.regulation_cited,
                ViolationIncident.penalty_amount,
                ViolationIncident.penalty_status,
            )
            .join(HSEIncident, ViolationIncident.hse_incident_id == HSEIncident.id)
            .order_by(ViolationIncident.id)
        )


COUNT_COLUMNS = [
    "total_incidents",
    "fatality_count",
    "lost_time_count",
    "recordable_count",
    "near_miss_count",
    "minor_count",
]


class StatisticsQuery(_HSEQuery):
    """Sum stored counts by a validated grouping; NULL-only sums remain NULL."""

    query_id = "hse.statistics"
    model = SafetyStatistic
    filters: ClassVar[list[FilterSpec]] = [
        FilterSpec("operators", "operator", "list"),
        FilterSpec("fields", "field", "list"),
        FilterSpec("years", None, "year"),
    ]
    extra_filters: ClassVar[set[str]] = {"metric", "grouping"}
    columns: ClassVar[list[str]] = [
        "report_date",
        "operator",
        "field_name",
    ] + COUNT_COLUMNS
    result_columns = columns
    _list_filter_columns: ClassVar[dict] = {
        "operators": SafetyStatistic.operator,
        "fields": SafetyStatistic.field_name,
    }
    _year_column = SafetyStatistic.report_date

    def _select(self, normalized):
        metric, grouping = normalized["metric"], normalized["grouping"]
        names = [metric] if metric else COUNT_COLUMNS
        # SQL SUM over supplied counts; no incidence rate or exposure is inferred.
        if grouping:
            group_column = getattr(self.model, grouping)
            sums = [func.sum(getattr(self.model, name)).label(name) for name in names]
            return (
                select(group_column, *sums)
                .group_by(group_column)
                .order_by(group_column)
            )
        names = ["report_date", "operator", "field_name"] + names
        return select(*(getattr(self.model, name) for name in names)).order_by(
            self.model.id
        )


class EpaTriQuery(_HSEQuery):
    """Query stored toxic releases; carcinogen evidence is absent in this schema."""

    query_id = "hse.epa_tri"
    model = ToxicRelease
    filters: ClassVar[list[FilterSpec]] = [
        FilterSpec("naics_codes", "naics", "list"),
        FilterSpec("chemicals", "chemical", "list"),
        FilterSpec("states", "state", "list"),
        FilterSpec("years", None, "year"),
    ]
    extra_filters: ClassVar[set[str]] = {"chemical_carcinogen"}
    columns: ClassVar[list[str]] = [
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
    _list_filter_columns: ClassVar[dict] = {
        "naics_codes": ToxicRelease.naics_code,
        "chemicals": ToxicRelease.chemical_name,
        "states": ToxicRelease.state,
    }
    _year_column = ToxicRelease.reporting_year
    _year_is_int = True


class OshaQuery(IncidentsQuery):
    """Query OSHA-prefixed records; industry and dedup completeness stay unverified."""

    query_id = "hse.osha"
    filters: ClassVar[list[FilterSpec]] = [
        spec for spec in IncidentsQuery.filters if spec.name != "sources"
    ] + [
        FilterSpec("naics_codes", "naics", "list"),
    ]


class HSEApi:
    """Own one configured connection pool shared by all five query surfaces."""

    def __init__(self, config: HSEQueryConfig):
        self._backend = HSEBackend(config)
        self.incidents = IncidentsQuery(backend=self._backend)
        self.penalties = PenaltiesQuery(backend=self._backend)
        self.statistics = StatisticsQuery(backend=self._backend)
        self.epa_tri = EpaTriQuery(backend=self._backend)
        self.osha = OshaQuery(backend=self._backend)

    def close(self):
        self._backend.close()

    async def aclose(self):
        await self._backend.aclose()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        await self.aclose()


# Compatibility demonstration surfaces; configured use goes through HSEApi.
incidents = IncidentsQuery()
penalties = PenaltiesQuery()
statistics = StatisticsQuery()
epa_tri = EpaTriQuery()
osha = OshaQuery()
