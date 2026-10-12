"""Pure pilot algebra: each quarter-quarter is exactly 40 acres.

Lots, irregular surveys and multiple sections are outside this geometry model.
Reported acreage is screening evidence, never ownership or title evidence.
"""

from datetime import date, datetime
from itertools import combinations
from typing import Literal

from .models import (
    AcreageEvidenceResult,
    AcreageException,
    AcreageRollup,
    FederalLandRecord,
    RecordEvidence,
    SourcedValue,
    SourceRef,
    TractOfInterest,
)

HECTARES_TO_ACRES = 2.4710538147
ROLLUP_KEYS = tuple(AcreageRollup.model_fields)


def available(value: float, source_id: str) -> SourcedValue:
    return SourcedValue(value=value, status="available", source_id=source_id)


def marker(
    note: str, status: Literal["unavailable", "ambiguous"] = "unavailable"
) -> SourcedValue:
    return SourcedValue(value=None, status=status, source_id=None, note=note)


def _stale_status(record: FederalLandRecord, as_of: date) -> bool:
    stale = record.record_status in {"pending", "unknown"}
    stale |= record.record_status == "active" and (
        (record.expiration_date is not None and record.expiration_date < as_of)
        or (record.effective_date is not None and record.effective_date > as_of)
    )
    stale |= (
        record.record_status == "expired"
        and record.expiration_date is not None
        and record.expiration_date >= as_of
    )
    return stale


def _check_area(
    record: FederalLandRecord,
    area: float,
    intersect: set[str],
    exceptions: list[AcreageException],
) -> tuple[SourcedValue, bool]:
    area_value = available(area, record.source_id)
    uncertain = False
    if record.aliquots is not None and abs(area - 40 * len(record.aliquots)) > 0.5:
        detail = "Converted record area differs from quarter-quarter geometry by over 0.5 acres."
        exceptions.append(
            AcreageException(
                kind="unit_ambiguous",
                record_serials=[record.record_serial],
                detail=detail,
            )
        )
        area_value = marker(detail, "ambiguous")
        uncertain = bool(intersect)
    return area_value, uncertain


def _inspect_record(
    record: FederalLandRecord, tract_set: set[str], source: SourceRef
) -> tuple[RecordEvidence, set[str], list[AcreageException], bool]:
    exceptions: list[AcreageException] = []
    area = record.area.value * (
        HECTARES_TO_ACRES if record.area.unit == "hectares" else 1
    )
    intersect = tract_set & set(record.aliquots or [])
    intersect_value = available(len(intersect) * 40.0, record.source_id)
    kind: Literal["missing_geometry", "non_intersecting"] | None
    if record.aliquots is None:
        kind, detail = (
            "missing_geometry",
            "Geometry is unavailable; excluded from rollup.",
        )
        intersect_value = marker(detail)
    elif not intersect:
        kind, detail = "non_intersecting", "Record does not intersect the tract."
    else:
        kind, detail = None, ""
    if kind:
        exceptions.append(
            AcreageException(
                kind=kind, record_serials=[record.record_serial], detail=detail
            )
        )
    area_value, uncertain = _check_area(record, area, intersect, exceptions)
    stale = _stale_status(record, source.retrieved_at.date())
    if stale:
        exceptions.append(
            AcreageException(
                kind="stale_status",
                record_serials=[record.record_serial],
                detail="Status is unresolved or inconsistent with data date.",
            )
        )
        uncertain |= bool(intersect)
    evidence = RecordEvidence(
        **record.model_dump(),
        intersect_acres=intersect_value,
        area_acres=area_value,
        retrieved_at=source.retrieved_at,
    )
    return evidence, intersect, exceptions, uncertain


def _provenance(
    tract: TractOfInterest, sources: list[SourceRef]
) -> tuple[list[SourceRef], datetime, str]:
    if not sources or len({s.source_id for s in sources}) != len(sources):
        raise ValueError("Unique source references are required")
    if any(
        s.source_id in {"tract-input", "federal-record-rollup", "derived-no-record"}
        for s in sources
    ):
        raise ValueError("Reserved source reference")
    sources = sorted(sources, key=lambda s: s.source_id)
    as_of = min(s.retrieved_at for s in sources)
    kind: Literal["fixture", "live"] = (
        "fixture" if any(s.kind == "fixture" for s in sources) else "live"
    )
    refs = sources + [
        SourceRef(
            source_id="tract-input",
            dataset="Tract input: " + tract.tract_id,
            kind=kind,
            retrieved_at=as_of,
            license_note="Caller-supplied screening geometry.",
        )
    ]
    rollup_source = sources[0].source_id
    if len(sources) > 1:
        rollup_source = "federal-record-rollup"
        refs.append(
            SourceRef(
                source_id=rollup_source,
                dataset="Union of sources: " + ", ".join(s.source_id for s in sources),
                kind=kind,
                retrieved_at=as_of,
                license_note="Derived from listed source references.",
            )
        )
    return refs, as_of, rollup_source


def _rollup(
    tract: TractOfInterest,
    coverage: set[str],
    leased: set[str],
    nonleased: set[str],
    uncertain: bool,
    source: str,
) -> AcreageRollup:
    if not coverage:
        return AcreageRollup(
            **{key: marker("No usable intersecting records.") for key in ROLLUP_KEYS}
        )
    values = dict(
        gross_area_acres=available(tract.gross_area_acres, "tract-input"),
        federal_record_coverage_acres=available(len(coverage) * 40.0, source),
        leased_acres=available(len(leased) * 40.0, source),
        expired_or_nonleased_acres=available(len(nonleased) * 40.0, source),
        no_record_acres=SourcedValue(
            value=tract.gross_area_acres - len(coverage) * 40.0,
            status="available",
            source_id="derived-no-record",
            note=(
                "derived: tract gross area minus federal-record coverage; "
                "not a federal-record value"
            ),
        ),
    )
    if uncertain or leased & nonleased:
        for key in ("leased_acres", "expired_or_nonleased_acres"):
            values[key] = marker(
                "Units or status prevent an unambiguous lease split.", "ambiguous"
            )
    return AcreageRollup(**values)


def _summarize_records(
    tract: TractOfInterest, records: list[FederalLandRecord], sources: list[SourceRef]
) -> tuple[
    list[RecordEvidence], list[AcreageException], set[str], set[str], set[str], bool
]:
    source_map = {s.source_id: s for s in sources}
    if len({r.record_serial for r in records}) != len(records):
        raise ValueError("Duplicate record serials")
    evidence: list[RecordEvidence] = []
    exceptions: list[AcreageException] = []
    intersections: list[tuple[str, set[str]]] = []
    coverage: set[str] = set()
    leased: set[str] = set()
    nonleased: set[str] = set()
    uncertain = False
    for record in sorted(records, key=lambda r: r.record_serial):
        if record.source_id not in source_map:
            raise ValueError("Record source reference is missing")
        item, intersect, issues, unresolved = _inspect_record(
            record, set(tract.aliquots), source_map[record.source_id]
        )
        evidence.append(item)
        exceptions.extend(issues)
        intersections.append((record.record_serial, intersect))
        coverage |= intersect
        uncertain |= unresolved
        if not unresolved:
            bucket = (
                leased
                if record.record_type == "lease" and record.record_status == "active"
                else nonleased
            )
            bucket |= intersect
    for (a, left), (b, right) in combinations(intersections, 2):
        if left & right:
            exceptions.append(
                AcreageException(
                    kind="overlap",
                    record_serials=[a, b],
                    acres=len(left & right) * 40.0,
                    detail="Double-claimed geometry; coverage union counts it once.",
                )
            )
    return evidence, exceptions, coverage, leased, nonleased, uncertain


def evaluate(
    tract: TractOfInterest, records: list[FederalLandRecord], sources: list[SourceRef]
) -> AcreageEvidenceResult:
    """Screen validated tract records without I/O or a wall-clock dependency."""
    refs, as_of, rollup_source = _provenance(tract, sources)
    evidence, exceptions, coverage, leased, nonleased, uncertain = _summarize_records(
        tract, records, sources
    )
    acreage = _rollup(tract, coverage, leased, nonleased, uncertain, rollup_source)
    if acreage.no_record_acres.value is not None:
        refs.append(
            SourceRef(
                source_id="derived-no-record",
                dataset="Derived from tract-input and " + rollup_source,
                kind=refs[-1].kind,
                retrieved_at=as_of,
                license_note="Derived from listed source references.",
            )
        )
    reasons = ["exceptions_present"] if exceptions else []
    status: Literal["evidence_complete", "evidence_partial", "evidence_blocked"]
    if not coverage:
        status, reasons = "evidence_blocked", reasons + ["no_usable_records"]
    elif exceptions or acreage.no_record_acres.value:
        status = "evidence_partial"
        if acreage.no_record_acres.value:
            reasons.append("tract_area_without_records")
    else:
        status, reasons = "evidence_complete", ["full_federal_record_coverage"]
    return AcreageEvidenceResult(
        screening_status=status,
        screening_reasons=reasons,
        tract=tract,
        acreage=acreage,
        records=evidence,
        exceptions=exceptions,
        sources=refs,
        data_as_of=as_of,
    )
