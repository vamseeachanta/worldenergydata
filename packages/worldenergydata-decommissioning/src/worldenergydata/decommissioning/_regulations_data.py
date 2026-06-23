# ABOUTME: Raw regulatory records for offshore decommissioning jurisdictions.
# ABOUTME: Populated with BSEE, NSTA, PSA, and ANP requirements. Import via regulations.py.

"""Static regulatory record data for BSEE, NSTA, PSA, and ANP.

This is a private data module. Use regulations.py public API instead.
"""

from worldenergydata.decommissioning._regulations_model import DecommissioningRegulation

# ---------------------------------------------------------------------------
# BSEE – Gulf of Mexico (15 records)
# ---------------------------------------------------------------------------

_BSEE: list[DecommissioningRegulation] = [
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="well_plugging",
        lead_time_months=6,
        key_threshold="Wells idle >5 years must be permanently plugged or justified",
        reference_doc="BSEE NTL 2018-N02",
        notes="Idle Iron initiative; applies to all OCS wells",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="structure_removal",
        lead_time_months=12,
        key_threshold=(
            "Platforms in <300 ft must be removed within 1 year of "
            "production cessation"
        ),
        reference_doc="30 CFR 250.1725",
        notes="Shallowest water deadline is most stringent",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="pipeline_decommission",
        lead_time_months=6,
        key_threshold="Pipelines must be flushed, filled, and either removed or buried",
        reference_doc="30 CFR 250.1750",
        notes="Abandonment-in-place requires burial or approved protective cover",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="environmental_survey",
        lead_time_months=3,
        key_threshold="Pre-decommissioning environmental survey required for all platforms",
        reference_doc="BSEE NTL 2016-N04",
        notes="Survey must cover 500 m radius around structure",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="decommissioning_plan",
        lead_time_months=24,
        key_threshold="Decommissioning Application required 2 years before planned cessation",
        reference_doc="30 CFR 250.1703",
        notes="Includes site clearance, pipeline removal, and well P&A plans",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="financial_assurance",
        lead_time_months=3,
        key_threshold=(
            "Operators must demonstrate financial assurance for all "
            "decommissioning obligations"
        ),
        reference_doc="30 CFR 250.1703(b)",
        notes="Bonds or approved alternatives required",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="reel_clearance",
        lead_time_months=6,
        key_threshold=(
            "Subsea equipment and templates must be removed within "
            "1 year of lease expiration"
        ),
        reference_doc="30 CFR 250.1740",
        notes="Includes flowline risers, umbilicals, and manifolds",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="site_clearance",
        lead_time_months=12,
        key_threshold=(
            "Site must be cleared to within 3 m of seabed after " "structure removal"
        ),
        reference_doc="30 CFR 250.1743",
        notes="Debris survey required post-clearance",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="artificial_reef",
        lead_time_months=18,
        key_threshold=(
            "Rigs-to-reefs conversion permitted; platform must be >40 ft "
            "below surface and 4+ miles from shipping lanes"
        ),
        reference_doc="BSEE Rigs-to-Reefs Guidelines 2019",
        notes="State concurrence required; topsides still removed",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="concurrent_obligations",
        lead_time_months=6,
        key_threshold=(
            "Shared-asset operators must coordinate decommissioning "
            "obligations and liabilities"
        ),
        reference_doc="30 CFR 250.1709",
        notes="Predecessor liability provisions apply",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="subsea_well_plugging",
        lead_time_months=9,
        key_threshold=(
            "Subsea wells idle >3 years must be temporarily or permanently "
            "plugged to surface"
        ),
        reference_doc="BSEE NTL 2020-N01",
        notes="Dual-barrier requirements apply for all plugged wells",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="conductor_removal",
        lead_time_months=6,
        key_threshold="Conductors must be cut to 15 ft below mudline after P&A",
        reference_doc="30 CFR 250.1726",
        notes="Applies to all permanently plugged wells",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="third_party_verification",
        lead_time_months=3,
        key_threshold=(
            "Independent verification required for P&A of wells with "
            "H2S concentrations"
        ),
        reference_doc="30 CFR 250.1721",
        notes="Third-party well examiners must be BSEE-approved",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="decommissioning_report",
        lead_time_months=1,
        key_threshold=(
            "Final decommissioning report must be submitted within "
            "30 days of completion"
        ),
        reference_doc="30 CFR 250.1780",
        notes="Includes as-built drawings and verified site clearance records",
    ),
    DecommissioningRegulation(
        region="gom",
        regulatory_body="BSEE",
        requirement_type="offshore_fishing_permit",
        lead_time_months=3,
        key_threshold=(
            "Commercial fishing exclusion zones require advance "
            "notice and permit coordination"
        ),
        reference_doc="BSEE Fisheries Consultation Policy 2021",
        notes="Essential fish habitat consultation may be required",
    ),
]

# ---------------------------------------------------------------------------
# NSTA – UK Continental Shelf (10 records)
# ---------------------------------------------------------------------------

_NSTA: list[DecommissioningRegulation] = [
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="decommissioning_programme",
        lead_time_months=24,
        key_threshold=(
            "Decommissioning Programme must be submitted and approved "
            "before any decommissioning activity begins"
        ),
        reference_doc="Petroleum Act 1998 s.29",
        notes="NSTA (formerly OGA) approval required; public consultation often triggered",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="structure_removal",
        lead_time_months=36,
        key_threshold=(
            "All platforms >4000 tonnes must be fully removed under "
            "OSPAR Decision 98/3"
        ),
        reference_doc="OSPAR Decision 98/3",
        notes="Derogations possible only for concrete gravity-based structures",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="well_plugging",
        lead_time_months=12,
        key_threshold=(
            "All wells must be permanently plugged to surface with "
            "cement barriers per CS3 requirements"
        ),
        reference_doc="NSTA CS3 Well Decommissioning Guidelines 2018",
        notes="Well integrity competency verification required",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="pipeline_decommission",
        lead_time_months=18,
        key_threshold=(
            "Pipeline abandonment-in-place permitted if no navigational "
            "hazard and sediment coverage demonstrated"
        ),
        reference_doc="OSPAR Guidelines 2009/1",
        notes="Pipeline owner liability remains post-abandonment",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="environmental_survey",
        lead_time_months=6,
        key_threshold=(
            "Environmental survey required pre- and post-decommissioning "
            "per CEFAS guidance"
        ),
        reference_doc="CEFAS Decommissioning Survey Guidance 2020",
        notes="Habitat and species impact assessment included",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="cost_recovery",
        lead_time_months=3,
        key_threshold=(
            "Tax relief (50% for ring-fence expenditure) recoverable "
            "for qualifying decommissioning costs"
        ),
        reference_doc="Finance Act 2012 s.164",
        notes="Predecessor liabilities eligible; HMRC clearance advised",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="sec12_liability",
        lead_time_months=6,
        key_threshold=(
            "Section 29 notices can be served on any party who was "
            "party to the production licence"
        ),
        reference_doc="Petroleum Act 1998 s.34",
        notes="Joint and several liability for decommissioning obligations",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="decommissioning_security",
        lead_time_months=12,
        key_threshold=(
            "Security arrangements required where counterparty credit "
            "risk is assessed as material"
        ),
        reference_doc="NSTA Decommissioning Security Guidance 2021",
        notes="Letters of credit or escrow accounts accepted",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="ospar_reporting",
        lead_time_months=3,
        key_threshold=(
            "Annual OSPAR Offshore Industry Committee reporting "
            "on decommissioning progress required"
        ),
        reference_doc="OSPAR Decision 98/3 Annex II",
        notes="Data submitted via UK Hydrographic Office notification",
    ),
    DecommissioningRegulation(
        region="ukcs",
        regulatory_body="NSTA",
        requirement_type="concurrent_activity",
        lead_time_months=6,
        key_threshold=(
            "Concurrent production and decommissioning activities require "
            "separate safety case assessment"
        ),
        reference_doc="HSE Offshore Installations (Safety Case) Regulations 2005",
        notes="Simultaneous operations (SIMOPS) risk assessment mandatory",
    ),
]

# ---------------------------------------------------------------------------
# PSA – Norwegian Continental Shelf (8 records)
# ---------------------------------------------------------------------------

_PSA: list[DecommissioningRegulation] = [
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="decommissioning_plan",
        lead_time_months=36,
        key_threshold=(
            "Disposal plan must be submitted to Ministry of Energy "
            "at least 5 years before field cessation"
        ),
        reference_doc="Norwegian Petroleum Act §5-1",
        notes="Plan includes well P&A, pipeline, and installation disposal options",
    ),
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="well_plugging",
        lead_time_months=12,
        key_threshold=(
            "All wells must be permanently plugged with minimum two "
            "independent barriers per well"
        ),
        reference_doc="PSA Well Regulations §88",
        notes="Competent authority well examination required",
    ),
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="structure_removal",
        lead_time_months=24,
        key_threshold=(
            "Floating installations shall be removed; concrete gravity "
            "structures evaluated case by case"
        ),
        reference_doc="Norwegian Petroleum Act §5-3",
        notes="OSPAR Decision 98/3 incorporated into Norwegian law",
    ),
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="pipeline_decommission",
        lead_time_months=18,
        key_threshold=(
            "Pipelines must be cleaned and assessed for reuse or "
            "abandonment; 5-year post-abandonment monitoring required"
        ),
        reference_doc="Norwegian Petroleum Regulations §47",
        notes="Seabed impact and trawling risk assessed by NPD",
    ),
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="environmental_survey",
        lead_time_months=6,
        key_threshold=(
            "Pre-decommissioning seabed survey and post-decommissioning "
            "verification survey required"
        ),
        reference_doc="PSA Management Regulations §17",
        notes="Survey data reported to Norwegian Environment Agency (NEA)",
    ),
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="hsseq_plan",
        lead_time_months=6,
        key_threshold=(
            "HSSEQ plan for decommissioning phase mandatory; "
            "major accident risk assessment required"
        ),
        reference_doc="PSA Management Regulations §11",
        notes="Covers lifting operations, diving, and structural removal risks",
    ),
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="ministerial_consent",
        lead_time_months=24,
        key_threshold=(
            "Ministry of Energy must approve final disposal before "
            "execution; Parliamentary notification for major fields"
        ),
        reference_doc="Norwegian Petroleum Act §5-3",
        notes="Consent required separately from initial disposal plan approval",
    ),
    DecommissioningRegulation(
        region="ncs",
        regulatory_body="PSA",
        requirement_type="contractor_qualification",
        lead_time_months=6,
        key_threshold=(
            "All marine contractors performing removal operations must "
            "hold PSA acknowledgment of compliance (AoC)"
        ),
        reference_doc="PSA Facilities Regulations §§ 6-10",
        notes="Applies to heavy-lift vessels and diving support vessels",
    ),
]

# ---------------------------------------------------------------------------
# ANP – Brazil (6 records)
# ---------------------------------------------------------------------------

_ANP: list[DecommissioningRegulation] = [
    DecommissioningRegulation(
        region="brazil",
        regulatory_body="ANP",
        requirement_type="decommissioning_plan",
        lead_time_months=30,
        key_threshold=(
            "Decommissioning plan required at least 5 years before "
            "planned cessation per ANP Resolution 817/2020"
        ),
        reference_doc="ANP Resolution 817/2020",
        notes="Plan must include environmental, social, and financial details",
    ),
    DecommissioningRegulation(
        region="brazil",
        regulatory_body="ANP",
        requirement_type="well_plugging",
        lead_time_months=12,
        key_threshold=(
            "Wells must be plugged per ABNT NBR 15544 and " "ANP technical requirements"
        ),
        reference_doc="ANP Portaria 25/2002 updated by Resolution 817/2020",
        notes="IBAMA environmental license required before P&A of complex wells",
    ),
    DecommissioningRegulation(
        region="brazil",
        regulatory_body="ANP",
        requirement_type="structure_removal",
        lead_time_months=24,
        key_threshold=(
            "Platforms and floating production systems must be removed; "
            "artificial reef option available under IBAMA approval"
        ),
        reference_doc="ANP Resolution 817/2020 Art. 15",
        notes="Navy coordination required for offshore removal operations",
    ),
    DecommissioningRegulation(
        region="brazil",
        regulatory_body="ANP",
        requirement_type="pipeline_decommission",
        lead_time_months=18,
        key_threshold=(
            "Pipelines may be abandoned in place if structural and "
            "environmental risk assessment approved by ANP and IBAMA"
        ),
        reference_doc="ANP Resolution 817/2020 Art. 22",
        notes="Includes umbilicals, risers, and export lines",
    ),
    DecommissioningRegulation(
        region="brazil",
        regulatory_body="ANP",
        requirement_type="environmental_license",
        lead_time_months=24,
        key_threshold=(
            "IBAMA environmental license required for decommissioning "
            "activities in Brazilian exclusive economic zone"
        ),
        reference_doc="IBAMA IN 184/2008",
        notes="EIA/RIMA required for major offshore structures",
    ),
    DecommissioningRegulation(
        region="brazil",
        regulatory_body="ANP",
        requirement_type="financial_guarantee",
        lead_time_months=6,
        key_threshold=(
            "Financial guarantee (bond or escrow) equal to full "
            "estimated decommissioning cost required"
        ),
        reference_doc="ANP Resolution 817/2020 Art. 7",
        notes="Guarantee must be updated annually; ANP may adjust estimate",
    ),
]

# ---------------------------------------------------------------------------
# Combined flat list — all 39 records
# ---------------------------------------------------------------------------

ALL_REGULATIONS: list[DecommissioningRegulation] = _BSEE + _NSTA + _PSA + _ANP
