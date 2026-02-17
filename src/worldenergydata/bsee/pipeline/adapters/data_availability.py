"""Data availability matrix for WRK-018 Phase 1.

Documents what data is available from each regulatory source across the 6
analysis domains defined by the BSEE field pipeline (WRK-017).

Status levels:
    AVAILABLE — Data loader exists, field mapping is clear, data is accessible
    PARTIAL   — Some data exists but coverage is incomplete
    UNAVAILABLE — No data loader, endpoint, or public data source
"""

from __future__ import annotations

from worldenergydata.bsee.pipeline.adapters.common_schema import (
    DataAvailability,
    DomainStatus,
)

# ---------------------------------------------------------------------------
# BSEE (US Federal Offshore) — Reference implementation
# ---------------------------------------------------------------------------
BSEE_AVAILABILITY = DataAvailability(
    source_id="bsee",
    source_name="Bureau of Safety and Environmental Enforcement",
    jurisdiction="US Federal Offshore (Gulf of Mexico, Alaska, Pacific)",
    wellbore=DomainStatus(
        status="available",
        notes="AllFieldsRunner + FieldNameResolver. Wellbore counts by lease, "
        "field, area code, and geological region.",
    ),
    well_path=DomainStatus(
        status="partial",
        notes="Directional survey data exists in BSEE tables but requires LFS "
        "pull for binary data files (129/133 are LFS stubs).",
    ),
    casing=DomainStatus(
        status="available",
        notes="well_tubulars.csv provides casing size, grade, weight, depth. "
        "SVG schematic and tabular matrix generation via casing_schematic.py.",
    ),
    drilling_completion=DomainStatus(
        status="available",
        notes="ComprehensiveActivityAnalyzer: 7-module WAR analyzer covering "
        "drilling efficiency, depth, era, cross-activity, lifecycle, operator, "
        "benchmarking. Spud dates, duration, rig types, completion types.",
    ),
    intervention=DomainStatus(
        status="available",
        notes="analysis/intervention/ module: activity aggregation, enrichment, "
        "dashboards, field visualization, insight generator.",
    ),
    production=DomainStatus(
        status="available",
        notes="ProductionAPI12Analysis for per-well aggregation. "
        "mv_productionsum.bin (39 yr totals) materialized. Monthly data needs "
        "LFS pull.",
    ),
)

# ---------------------------------------------------------------------------
# SODIR (Norwegian Continental Shelf)
# ---------------------------------------------------------------------------
SODIR_AVAILABILITY = DataAvailability(
    source_id="sodir",
    source_name="Sodir / NPD FactPages",
    jurisdiction="Norwegian Continental Shelf",
    wellbore=DomainStatus(
        status="available",
        notes="Endpoint 5000 (wellbores). WellboreProcessor maps wlbField, "
        "wlbNpdidWellbore, wlbStatus, wlbPurpose. Counts via groupby on "
        "'field' column. No dedicated aggregator yet.",
    ),
    well_path=DomainStatus(
        status="partial",
        notes="Surface lat/lon, UTM coords, max_inclination_deg available. "
        "Full deviation survey (MD/inc/azi station tables) not registered — "
        "SODIR API publishes it but endpoint not in endpoints.py.",
    ),
    casing=DomainStatus(
        status="unavailable",
        notes="SODIR FactPages publishes casing data (~endpoint 5100) but "
        "not registered in endpoints.py. No CasingProcessor exists.",
    ),
    drilling_completion=DomainStatus(
        status="partial",
        notes="Spud date (wlbDrillingStartDate), completion date, drilling "
        "duration (calculated), operator, well purpose. Missing: rig name/"
        "type, completion type (open hole, perf, gravel pack).",
    ),
    intervention=DomainStatus(
        status="unavailable",
        notes="SODIR does not publish a discrete workover register. "
        "Intervention activity would need to be inferred from wellbore "
        "status transitions, which requires historical snapshots.",
    ),
    production=DomainStatus(
        status="partial",
        notes="Field-level cumulative totals and reserves via FieldProcessor "
        "(endpoint 7100): cum oil/gas/NGL/condensate, recoverable, recovery "
        "factor. Monthly time-series endpoint (~7200) not registered. "
        "No per-well production allocation.",
    ),
)

# ---------------------------------------------------------------------------
# Texas RRC (Railroad Commission of Texas)
# ---------------------------------------------------------------------------
RRC_AVAILABILITY = DataAvailability(
    source_id="rrc",
    source_name="Railroad Commission of Texas",
    jurisdiction="Texas onshore and state waters",
    wellbore=DomainStatus(
        status="available",
        notes="PDQ wellbore dump (wellboredump.zip). WellProcessor: "
        "summarize_by_district() gives total/active/plugged/horizontal wells. "
        "field_name column available for field-level groupby.",
    ),
    well_path=DomainStatus(
        status="partial",
        notes="Well type classification (HZ=horizontal, DI=directional), "
        "wellbore_profile, lat/lon, total_depth. No survey station data "
        "(MD/inc/azi) — not in PDQ public dumps.",
    ),
    casing=DomainStatus(
        status="unavailable",
        notes="Not in PDQ bulk download system. W-2 Casing Record exists "
        "in RRC filing system but no programmatic endpoint wired.",
    ),
    drilling_completion=DomainStatus(
        status="available",
        notes="Drilling permits: permit_number, approved_date, permit_type, "
        "total_depth, horizontal_length. Completions: completion_date, "
        "formation, perforation top/bottom, initial_production. "
        "PermitProcessor classifies new_drill, recompletion, sidetrack, etc.",
    ),
    intervention=DomainStatus(
        status="partial",
        notes="Plug dates and P&A status from wellbore dump. Workover permit "
        "counts derivable from drilling permits (type='workover'). No "
        "detailed workover job records or W-12 plugging reports.",
    ),
    production=DomainStatus(
        status="available",
        notes="Monthly production by lease: oil (BBL), gas (MCF), condensate, "
        "water, well_count. BOE calculation. Aggregatable by district, lease, "
        "field_name, month/year. Lease-level only (no per-well allocation).",
    ),
)

# ---------------------------------------------------------------------------
# Mexico CNH (Comisión Nacional de Hidrocarburos)
# ---------------------------------------------------------------------------
CNH_AVAILABILITY = DataAvailability(
    source_id="cnh",
    source_name="Comisión Nacional de Hidrocarburos",
    jurisdiction="Mexican offshore and onshore",
    wellbore=DomainStatus(
        status="unavailable",
        notes="SIHScraper.export_well_data() and CNHExcelLoader."
        "parse_well_report() are implemented, but MexicoCNHData."
        "_collect_wells() is a stub returning []. No data on disk.",
    ),
    well_path=DomainStatus(
        status="unavailable",
        notes="No survey endpoint. 'trayectoria' field in Excel schema is "
        "a scalar classification, not station survey data.",
    ),
    casing=DomainStatus(
        status="unavailable",
        notes="SIH portal does not expose casing program data. No endpoint, "
        "scraper method, or column mapping for casing.",
    ),
    drilling_completion=DomainStatus(
        status="partial",
        notes="Scraper + parser infrastructure exists for well data "
        "(fecha_inicio, fecha_terminacion, tipo_pozo, formacion, "
        "profundidad_total). Collector stub not wired. No data on disk.",
    ),
    intervention=DomainStatus(
        status="unavailable",
        notes="SIH portal scope is production/contract reporting, not "
        "operational events. No workover data source identified.",
    ),
    production=DomainStatus(
        status="partial",
        notes="Strongest domain. SIHScraper.export_production_data() is "
        "fully implemented (Selenium). CNHExcelLoader.parse_production_report() "
        "handles oil/gas/water/condensate/cumulative columns. CNHPDFParser "
        "also available. Collector stub not wired. No data on disk.",
    ),
)

# ---------------------------------------------------------------------------
# Brazil ANP (Agência Nacional do Petróleo)
# ---------------------------------------------------------------------------
ANP_AVAILABILITY = DataAvailability(
    source_id="anp",
    source_name="Agência Nacional do Petróleo, Gás Natural e Biocombustíveis",
    jurisdiction="Brazilian offshore and onshore (pre-salt and conventional)",
    wellbore=DomainStatus(
        status="unavailable",
        notes="No ANP module exists in codebase. ANP open data portal "
        "publishes well data but no loader implemented.",
    ),
    well_path=DomainStatus(
        status="unavailable",
        notes="No module. Well trajectory data availability from ANP "
        "open data portal is unconfirmed.",
    ),
    casing=DomainStatus(
        status="unavailable",
        notes="No module. Casing program details not typically published "
        "by ANP in open data.",
    ),
    drilling_completion=DomainStatus(
        status="unavailable",
        notes="No module. ANP open data has well metadata (spud dates, "
        "depths) but no loader implemented.",
    ),
    intervention=DomainStatus(
        status="unavailable",
        notes="No module. Intervention data not available from ANP open data.",
    ),
    production=DomainStatus(
        status="unavailable",
        notes="No module. ANP publishes monthly production by field/well "
        "on its open data portal but no loader implemented.",
    ),
)

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
AVAILABILITY_MATRIX: dict[str, DataAvailability] = {
    "bsee": BSEE_AVAILABILITY,
    "sodir": SODIR_AVAILABILITY,
    "rrc": RRC_AVAILABILITY,
    "cnh": CNH_AVAILABILITY,
    "anp": ANP_AVAILABILITY,
}


def get_availability(source_id: str) -> DataAvailability:
    """Return data availability for a given source."""
    if source_id not in AVAILABILITY_MATRIX:
        raise ValueError(
            f"Unknown source '{source_id}'. "
            f"Available: {list(AVAILABILITY_MATRIX)}"
        )
    return AVAILABILITY_MATRIX[source_id]


def summary_table() -> list[dict[str, str]]:
    """Return a flat list of dicts suitable for DataFrame construction."""
    rows = []
    for source_id, avail in AVAILABILITY_MATRIX.items():
        for domain in [
            "wellbore",
            "well_path",
            "casing",
            "drilling_completion",
            "intervention",
            "production",
        ]:
            ds: DomainStatus = getattr(avail, domain)
            rows.append(
                {
                    "source": source_id,
                    "source_name": avail.source_name,
                    "domain": domain,
                    "status": ds.status,
                    "notes": ds.notes,
                }
            )
    return rows
