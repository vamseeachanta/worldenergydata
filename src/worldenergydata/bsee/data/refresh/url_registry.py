"""Static registry of BSEE dataset download URLs and expected bin files.

Maps each bin subdirectory to its ZIP download URL and the .bin files
that should exist after extraction.  OGOR-A yearly files (1996-2024 +
current) are generated programmatically.

Total expected stubs across all specs: 129.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

BSEE_BASE_URL = "https://www.data.bsee.gov"


@dataclass(frozen=True)
class DatasetSpec:
    """Describes one downloadable BSEE dataset."""

    bin_dir: str
    zip_url: str
    expected_bins: list[str]
    timeout_s: int = 600
    is_ogor_a: bool = False


def _url(path: str) -> str:
    return f"{BSEE_BASE_URL}/{path}"


# ── Regular (non-OGOR-A) specs ─────────────────────────────────────

_REGULAR_SPECS: tuple[DatasetSpec, ...] = (
    DatasetSpec("apichanges", _url("Well/Files/APIChangesRawData.zip"),
                ["mv_apichanges_all.bin"]),
    DatasetSpec("apiraw", _url("Well/Files/APIRawData.zip"),
                ["mv_api_list_all.bin", "mv_api_wellcomps_all.bin"]),
    DatasetSpec("approvals", _url("Company/Files/ApprovalsRawData.zip"),
                ["mv_approval_info.bin"]),
    DatasetSpec("assignments", _url("Leasing/Files/AssignmentsRawData.zip"),
                ["mv_assignments.bin"]),
    DatasetSpec("companydetails", _url("Company/Files/CompanyRawData.zip"),
                ["mv_companies_active.bin", "mv_companies_all.bin"]),
    DatasetSpec("decomcost", _url("Leasing/Files/DecomCostEstRawData.zip"),
                ["mv_decom_cost_estimates.bin", "mv_decom_cost_inst_pipe.bin",
                 "mv_decom_cost_inst_plat.bin", "mv_decom_cost_prop_pipe.bin",
                 "mv_decom_cost_prop_plat.bin", "mv_decom_cost_prop_well.bin",
                 "mv_decom_cost_spud_well.bin", "mv_decom_cost_totals.bin"]),
    DatasetSpec("deepqual", _url("Other/Files/DeepQualRawData.zip"),
                ["mv_deep_water_field_leases.bin"]),
    DatasetSpec("dsptsdelimit", _url("Well/Files/dsptsdelimit.ZIP"),
                ["dsptsdelimit.bin"]),
    DatasetSpec("fmp", _url("Production/Files/FMPRawData.zip"),
                ["mv_fmplist.bin", "mv_fmp_meas_locations.bin"]),
    DatasetSpec("incinv", _url("Other/Files/IncInvRawData.zip"),
                ["mv_acc_investigations.bin"]),
    DatasetSpec("incs", _url("Company/Files/INCSRawData.zip"),
                ["mv_incs_by_oper.bin", "mv_incs_fac_shutins_alaska.bin",
                 "mv_incs_fac_shutins_gulf.bin", "mv_incs_fac_shutins_pacific.bin",
                 "mv_incs_inspections_alaska.bin", "mv_incs_inspections_gulf.bin",
                 "mv_incs_inspections_pacific.bin", "mv_incs_shutins_alaska.bin",
                 "mv_incs_shutins_gulf.bin", "mv_incs_shutins_pacific.bin",
                 "mv_incs_warnings_alaska.bin", "mv_incs_warnings_gulf.bin",
                 "mv_incs_warnings_pacific.bin", "mv_insp_by_oper.bin"]),
    DatasetSpec("lab", _url("Leasing/Files/LABRawData.zip"),
                ["mv_lease_area_block.bin"]),
    DatasetSpec("leaseowner", _url("Leasing/Files/LeaseOwnerRawData.zip"),
                ["mv_lease_owners_main.bin"]),
    DatasetSpec("mcpflow", _url("Production/Files/MCPFlowRawData.zip"),
                ["mv_mcpflowareablock.bin", "mv_mcpflowleaseunits.bin",
                 "mv_mcpflowluoper.bin", "mv_mcpflowmeaslocations.bin",
                 "mv_mcpflowsubops.bin", "mv_mcpflowsystems.bin",
                 "mv_mcpflowunits.bin"]),
    DatasetSpec("nonrequired", _url("Leasing/Files/NonReqRawData.zip"),
                ["mv_nonrequired.bin"]),
    DatasetSpec("ocsprod", _url("Production/Files/OCSProdRawData.zip"),
                ["ocsprod_gasmonth.bin", "ocsprod_gasyear.bin",
                 "ocsprod_oilmonth.bin", "ocsprod_oilyear.bin"]),
    DatasetSpec("offshorestats", _url("Production/Files/OffshoreStatsRawData.zip"),
                ["mv_sbwd_apds.bin", "mv_sbwd_leases.bin",
                 "mv_sbwd_platforms.bin", "mv_sbwd_wells2.bin",
                 "mv_sbwd_wells.bin"]),
    DatasetSpec("osfr", _url("Leasing/Files/OSFRRawData.zip"),
                ["mv_osfr_companies.bin", "mv_osfr_information.bin",
                 "mv_osfr_segments.bin"]),
    DatasetSpec("permstruc", _url("Other/Files/PermStrucRawData.zip"),
                ["mv_perm_platforms.bin", "mv_subsea_boreholes.bin"]),
    DatasetSpec("pipeloc", _url("Pipeline/Files/PipeLocRawData.zip"),
                ["mv_pipelinelocation.bin"]),
    DatasetSpec("platstruc", _url("Platform/Files/PlatStrucRawData.zip"),
                ["mv_platstruc_authorityhist.bin", "mv_platstruc_cgrefcodes.bin",
                 "mv_platstruc_inccount.bin", "mv_platstruc_leases.bin",
                 "mv_platstruc_platformincs.bin", "mv_platstruc_rightofways.bin",
                 "mv_platstruc_ruers.bin", "mv_platstruc_structures.bin"]),
    DatasetSpec("production_plan_area", _url("Production/Files/ProdPlanAreaRawData.zip"),
                ["mv_pbpadata.bin"]),
    DatasetSpec("production_raw", _url("Production/Files/ProductionRawData.zip"),
                ["mv_productiondata.bin"]),
    DatasetSpec("rowdesc", _url("Pipeline/Files/RowDescRawData.zip"),
                ["mv_rowdescriptions.bin"]),
    DatasetSpec("royaltyref", _url("Other/Files/RoyaltyRefRawData.zip"),
                ["mv_preact.bin"]),
    DatasetSpec("scanneddocs", _url("Other/Files/ScannedDocsRawData.zip"),
                ["scan_active_inactive_leases.bin", "scan_adjudication_files.bin",
                 "scan_collateral_files.bin", "scan_company_files.bin",
                 "scan_dir_surveys.bin", "scan_expired_leases.bin",
                 "scan_gg_permits.bin", "scan_pipeline_maps.bin",
                 "scan_plans.bin", "scan_renleases.bin", "scan_row.bin",
                 "scan_sop_soo.bin", "scan_units.bin", "scan_well_files.bin",
                 "scan_well_potential_tests.bin"]),
    DatasetSpec("serialreg", _url("Leasing/Files/SerialRegRawData.zip"),
                ["mv_serreg_companies.bin", "mv_serreg_descriptions.bin",
                 "mv_serreg_high_bids.bin", "mv_serreg_lease_owner_assigns.bin",
                 "mv_serreg_lease_owner_groups.bin", "mv_serreg_lease_owner_remarks.bin",
                 "mv_serreg_lease_owners.bin", "mv_serreg_leases.bin",
                 "mv_serreg_portion_aliquots.bin", "mv_serreg_rates.bin",
                 "mv_serreg_remarks.bin", "mv_serreg_xys.bin"]),
    DatasetSpec("Well_APD_Default", _url("Well/Files/APDRawData.zip"),
                ["mv_apddata_all.bin", "mv_apd_main_all.bin"]),
)


# ── OGOR-A yearly specs (generated) ────────────────────────────────

def _build_ogor_a_specs() -> tuple[DatasetSpec, ...]:
    specs: list[DatasetSpec] = []
    bin_dir = "historical_production_yearly"
    for year in range(1996, 2025):
        specs.append(DatasetSpec(
            bin_dir=bin_dir,
            zip_url=_url(f"Production/Files/ogora{year}delimit.zip"),
            expected_bins=[f"ogora{year}delimit.bin"],
            is_ogor_a=True,
        ))
    specs.append(DatasetSpec(
        bin_dir=bin_dir,
        zip_url=_url("Production/Files/ogoradelimit.zip"),
        expected_bins=["ogoradelimit.bin"],
        is_ogor_a=True,
    ))
    return tuple(specs)


_OGOR_A_SPECS: tuple[DatasetSpec, ...] = _build_ogor_a_specs()


# ── Public API ──────────────────────────────────────────────────────

def get_regular_specs() -> Sequence[DatasetSpec]:
    """Return all non-OGOR-A dataset specs."""
    return _REGULAR_SPECS


def get_ogor_a_specs() -> Sequence[DatasetSpec]:
    """Return all OGOR-A yearly dataset specs."""
    return _OGOR_A_SPECS


def get_all_specs() -> Sequence[DatasetSpec]:
    """Return every dataset spec (regular + OGOR-A)."""
    return (*_REGULAR_SPECS, *_OGOR_A_SPECS)


def get_specs_for_dir(bin_dir: str) -> list[DatasetSpec]:
    """Return all specs whose *bin_dir* matches the given directory name."""
    return [s for s in get_all_specs() if s.bin_dir == bin_dir]
