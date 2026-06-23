"""
ABOUTME: Built-in well planning risk registry with 22 common drilling risks.
ABOUTME: Covers pressure management, wellbore integrity, rig capability, regulatory.
"""

from __future__ import annotations

from worldenergydata.well_planning.risk_model import (
    RiskAuthority,
    RiskCategory,
    RiskSeverity,
    WellPlanningRisk,
)

WELL_PLANNING_RISKS: list[WellPlanningRisk] = [
    # ------------------------------------------------------------------ #
    # OPERATIONAL — Project execution team can mitigate directly          #
    # ------------------------------------------------------------------ #
    WellPlanningRisk(
        risk_id="OP-001",
        title="Formation swelling clay",
        description=(
            "Reactive clay formations absorb water-based mud causing wellbore "
            "narrowing, pack-off events, and stuck pipe."
        ),
        category=RiskCategory.WELLBORE_INTEGRITY,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.HIGH,
        probability=0.6,
        risk_score=3 * 0.6,
        mitigation_owner="Drilling Engineer",
        mitigation_action=(
            "Switch to inhibitive KCl/polymer mud system; minimise open-hole "
            "exposure time; monitor shaker returns for clay discs."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Operational: Formation swelling clay identified "
            "in pre-drill data. Drilling Engineer to specify inhibitive mud "
            "system before spud. Confirm before mobilisation."
        ),
    ),
    WellPlanningRisk(
        risk_id="OP-002",
        title="Narrow mud weight window",
        description=(
            "Tight pore-pressure/fracture gradient spread leaves a mud weight "
            "window < 0.5 ppg, creating simultaneous kick and loss risk."
        ),
        category=RiskCategory.PRESSURE_MANAGEMENT,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.HIGH,
        probability=0.55,
        risk_score=3 * 0.55,
        mitigation_owner="Drilling Engineer",
        mitigation_action=(
            "Model ECD vs fracture gradient; plan back-pressure pump; consider "
            "MPD to dynamically manage equivalent circulating density."
        ),
        mpd_mitigation=True,
        escalation_template=(
            "ACTION REQUIRED — Operational: Mud weight window < 0.5 ppg. "
            "Drilling Engineer to validate ECD model and confirm MPD readiness "
            "before drilling 8.5-in section."
        ),
    ),
    WellPlanningRisk(
        risk_id="OP-003",
        title="BOP test failure",
        description=(
            "BOP pressure test fails acceptance criteria, delaying spud and "
            "risking well control capability."
        ),
        category=RiskCategory.WELLBORE_INTEGRITY,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.25,
        risk_score=2 * 0.25,
        mitigation_owner="Drilling Supervisor",
        mitigation_action=(
            "Pre-mobilisation BOP workshop; maintain seal inventory; schedule "
            "contingency test day in well programme."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Operational: BOP test failure risk. Drilling "
            "Supervisor to verify seal certification before rig move."
        ),
    ),
    WellPlanningRisk(
        risk_id="OP-004",
        title="Poor hole cleaning in deviated section",
        description=(
            "Cuttings beds accumulate in high-angle sections (>45 deg) causing "
            "pack-off, high torque, and stuck pipe."
        ),
        category=RiskCategory.HOLE_CLEANING,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.45,
        risk_score=2 * 0.45,
        mitigation_owner="Drilling Engineer",
        mitigation_action=(
            "Optimise flow rate for turbulent flow; schedule wiper trips; "
            "use rotary steerable to maintain RPM while sliding."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Operational: High inclination section requires "
            "hole-cleaning programme review. Drilling Engineer to confirm "
            "minimum flow rates and wiper-trip schedule."
        ),
    ),
    WellPlanningRisk(
        risk_id="OP-005",
        title="Lost circulation zone",
        description=(
            "Natural fractures or depleted sands cause drilling fluid losses "
            "exceeding 25 bbl/hr, risking hydrostatic imbalance."
        ),
        category=RiskCategory.PRESSURE_MANAGEMENT,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.HIGH,
        probability=0.4,
        risk_score=3 * 0.4,
        mitigation_owner="Drilling Engineer",
        mitigation_action=(
            "Pre-position LCM pills; lower mud weight to minimum required; "
            "model MPD back-pressure to compensate for losses."
        ),
        mpd_mitigation=True,
        escalation_template=(
            "ACTION REQUIRED — Operational: Lost circulation zone anticipated "
            "at projected depth. Pre-position LCM and confirm MPD back-pressure "
            "capability before entering zone."
        ),
    ),
    WellPlanningRisk(
        risk_id="OP-006",
        title="Differential sticking",
        description=(
            "High overbalance against permeable sands causes pipe to stick "
            "against the formation due to differential pressure."
        ),
        category=RiskCategory.WELLBORE_INTEGRITY,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.3,
        risk_score=2 * 0.3,
        mitigation_owner="Drilling Engineer",
        mitigation_action=(
            "Minimise overbalance; use pipe-dope spotting fluid contingency; "
            "maintain drill string rotation when on bottom."
        ),
        mpd_mitigation=True,
        escalation_template=(
            "ACTION REQUIRED — Operational: Differential sticking risk "
            "identified. Drilling Engineer to minimise overbalance and prepare "
            "spotting fluid programme."
        ),
    ),
    WellPlanningRisk(
        risk_id="OP-007",
        title="Inadequate formation evaluation coverage",
        description=(
            "Insufficient LWD/MWD coverage in reservoir section leads to "
            "incomplete geo-steering data and missed pay zones."
        ),
        category=RiskCategory.FORMATION_EVALUATION,
        authority=RiskAuthority.OPERATIONAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.35,
        risk_score=2 * 0.35,
        mitigation_owner="Petrophysicist",
        mitigation_action=(
            "Define minimum LWD suite in well programme; confirm real-time "
            "data transmission to office geo-steering team."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Operational: Formation evaluation tool string "
            "not confirmed. Petrophysicist to specify minimum LWD suite and "
            "confirm rig BHA compatibility."
        ),
    ),
    # ------------------------------------------------------------------ #
    # TACTICAL — Cross-functional team required for mitigation            #
    # ------------------------------------------------------------------ #
    WellPlanningRisk(
        risk_id="TC-001",
        title="Casing design insufficient for ECD loading",
        description=(
            "Planned casing grade or weight cannot sustain peak ECD + surge "
            "pressures during cementing operations."
        ),
        category=RiskCategory.PRESSURE_MANAGEMENT,
        authority=RiskAuthority.TACTICAL,
        severity=RiskSeverity.HIGH,
        probability=0.3,
        risk_score=3 * 0.3,
        mitigation_owner="Casing Design Engineer",
        mitigation_action=(
            "Run triaxial load analysis including ECD and surge/swab; upgrade "
            "casing grade if collapse/burst ratios < 1.15."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Tactical: Casing design must be validated for "
            "ECD loading. Casing Design Engineer and Drilling Engineer to "
            "complete triaxial analysis before AFE submission."
        ),
    ),
    WellPlanningRisk(
        risk_id="TC-002",
        title="Rig trip speed limitation",
        description=(
            "Maximum rig tripping speed exceeds safe swab pressure limit, "
            "risking induced influx on trips out."
        ),
        category=RiskCategory.HOLE_CLEANING,
        authority=RiskAuthority.TACTICAL,
        severity=RiskSeverity.LOW,
        probability=0.4,
        risk_score=1 * 0.4,
        mitigation_owner="Drilling Supervisor",
        mitigation_action=(
            "Calculate maximum trip speed from swab model; post trip sheet on "
            "rig floor; verify driller acceptance of limits."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Tactical: Trip speed limits must be calculated "
            "and communicated. Drilling Supervisor to post trip sheet before "
            "first trip out of hole."
        ),
    ),
    WellPlanningRisk(
        risk_id="TC-003",
        title="Wellhead pressure rating limit",
        description=(
            "Wellhead rated working pressure is below the anticipated shut-in "
            "wellhead pressure for worst-case influx scenario."
        ),
        category=RiskCategory.WELLBORE_INTEGRITY,
        authority=RiskAuthority.TACTICAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.2,
        risk_score=2 * 0.2,
        mitigation_owner="Completion Engineer",
        mitigation_action=(
            "Verify wellhead WP against MAASP; upgrade wellhead if required; "
            "confirm BOP accumulator can close under expected well pressure."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Tactical: Wellhead pressure rating requires "
            "verification against SIWHP. Completion Engineer to confirm "
            "wellhead selection before fabrication order."
        ),
    ),
    WellPlanningRisk(
        risk_id="TC-004",
        title="Pore pressure uncertainty in pre-salt",
        description=(
            "Limited offset well data in pre-salt target leads to high "
            "uncertainty in pore pressure prediction (±1 ppg)."
        ),
        category=RiskCategory.PRESSURE_MANAGEMENT,
        authority=RiskAuthority.TACTICAL,
        severity=RiskSeverity.HIGH,
        probability=0.5,
        risk_score=3 * 0.5,
        mitigation_owner="Geomechanics Engineer",
        mitigation_action=(
            "Build probabilistic PP/FG model; plan real-time pore pressure "
            "updates from LWD; carry contingency casing string."
        ),
        mpd_mitigation=True,
        escalation_template=(
            "ACTION REQUIRED — Tactical: Pore pressure uncertainty ±1 ppg in "
            "pre-salt. Geomechanics Engineer to deliver probabilistic model "
            "and contingency casing design before spud."
        ),
    ),
    WellPlanningRisk(
        risk_id="TC-005",
        title="Cement job quality in high-angle well",
        description=(
            "High wellbore inclination increases channelling risk during "
            "primary cementing, leaving uncemented annular sections."
        ),
        category=RiskCategory.WELLBORE_INTEGRITY,
        authority=RiskAuthority.TACTICAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.35,
        risk_score=2 * 0.35,
        mitigation_owner="Cement Engineer",
        mitigation_action=(
            "Model centraliser placement for stand-off > 67%; run CBL/VDL or "
            "ultrasonic tool to verify cement bond."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Tactical: High-angle cementing risk. Cement "
            "Engineer to confirm centraliser programme and post-job "
            "evaluation tool before mobilisation."
        ),
    ),
    WellPlanningRisk(
        risk_id="TC-006",
        title="Completion fluid compatibility with reservoir",
        description=(
            "Incompatibility between completion brine and reservoir fluids "
            "may cause scale deposition or formation damage."
        ),
        category=RiskCategory.COMPLETION,
        authority=RiskAuthority.TACTICAL,
        severity=RiskSeverity.MEDIUM,
        probability=0.3,
        risk_score=2 * 0.3,
        mitigation_owner="Completion Engineer",
        mitigation_action=(
            "Run fluid compatibility tests with reservoir fluid sample; select "
            "scale inhibitor package before completion design freeze."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ACTION REQUIRED — Tactical: Completion fluid compatibility testing "
            "required. Completion Engineer to coordinate lab test with "
            "Reservoir team before AFE sign-off."
        ),
    ),
    # ------------------------------------------------------------------ #
    # STRATEGIC — Corporate / procurement authority required              #
    # ------------------------------------------------------------------ #
    WellPlanningRisk(
        risk_id="ST-001",
        title="Rig MPD capability not in contract",
        description=(
            "Selected rig contract does not include MPD equipment or trained "
            "crew, preventing use of managed pressure drilling in narrow "
            "mud weight window sections."
        ),
        category=RiskCategory.RIG_CAPABILITY,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.HIGH,
        probability=0.5,
        risk_score=3 * 0.5,
        mitigation_owner="Contracts Manager",
        mitigation_action=(
            "Insert MPD equipment schedule into rig contract before signature; "
            "negotiate MPD crew day-rate and standby provisions."
        ),
        mpd_mitigation=True,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: Rig contract lacks MPD scope. "
            "Contracts Manager must include MPD equipment schedule and "
            "training obligations before contract execution."
        ),
    ),
    WellPlanningRisk(
        risk_id="ST-002",
        title="Regulatory approval timeline risk",
        description=(
            "Well permit or environmental approval is on the critical path; "
            "delays push spud date beyond weather window."
        ),
        category=RiskCategory.REGULATORY,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.MEDIUM,
        probability=0.4,
        risk_score=2 * 0.4,
        mitigation_owner="Regulatory Affairs Manager",
        mitigation_action=(
            "Submit permit application 6 months before spud; assign dedicated "
            "liaison to regulatory body; track approval milestones weekly."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: Permit approval timeline at risk. "
            "Regulatory Affairs Manager to confirm submission date and "
            "escalation path to Government liaison."
        ),
    ),
    WellPlanningRisk(
        risk_id="ST-003",
        title="Third-party MWD/LWD tool availability",
        description=(
            "Specialised LWD tools (e.g. sonic/nuclear) have long lead times "
            "and may not be available for planned spud date."
        ),
        category=RiskCategory.RIG_CAPABILITY,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.LOW,
        probability=0.35,
        risk_score=1 * 0.35,
        mitigation_owner="Contracts Manager",
        mitigation_action=(
            "Issue LWD tool reservation 90 days before spud; confirm backup "
            "vendor availability; include substitution clause in contract."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: LWD tool availability not "
            "confirmed. Contracts Manager to issue tool reservation and "
            "identify contingency vendor within 2 weeks."
        ),
    ),
    WellPlanningRisk(
        risk_id="ST-004",
        title="Operator drilling authority spend limits",
        description=(
            "Well AFE exceeds Drilling Manager authority; additional AFE "
            "approval requires executive sign-off with long lead times."
        ),
        category=RiskCategory.REGULATORY,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.MEDIUM,
        probability=0.3,
        risk_score=2 * 0.3,
        mitigation_owner="Wells Manager",
        mitigation_action=(
            "Pre-submit AFE with 20% contingency; identify approval chain and "
            "obtain preliminary sign-off before rig commitment."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: AFE exceeds authority limits. "
            "Wells Manager to initiate executive approval process no later "
            "than 60 days before rig commitment date."
        ),
    ),
    WellPlanningRisk(
        risk_id="ST-005",
        title="Mud system upgrade cost approval",
        description=(
            "Required high-performance synthetic mud system upgrade exceeds "
            "project OPEX budget and needs corporate approval."
        ),
        category=RiskCategory.PRESSURE_MANAGEMENT,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.LOW,
        probability=0.25,
        risk_score=1 * 0.25,
        mitigation_owner="Supply Chain Manager",
        mitigation_action=(
            "Present cost-benefit analysis of mud system upgrade vs NPT cost; "
            "obtain budget pre-approval in advance of rig contract."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: Mud system upgrade requires "
            "budget approval. Supply Chain Manager to submit cost-benefit "
            "analysis to leadership before rig contract signature."
        ),
    ),
    WellPlanningRisk(
        risk_id="ST-006",
        title="Rig selection suitability for HPHT environment",
        description=(
            "Proposed rig lacks HPHT BOP rating or high-pressure riser system "
            "needed for target reservoir conditions."
        ),
        category=RiskCategory.RIG_CAPABILITY,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.CRITICAL,
        probability=0.3,
        risk_score=4 * 0.3,
        mitigation_owner="Wells Director",
        mitigation_action=(
            "Re-evaluate rig selection criteria; shortlist only HPHT-rated "
            "units; confirm BOP rating against SIWHP before tender award."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: Rig HPHT suitability not "
            "confirmed. Wells Director must validate rig BOP rating against "
            "MAASP before tender award."
        ),
    ),
    WellPlanningRisk(
        risk_id="ST-007",
        title="MPD well control training not in rig crew contract",
        description=(
            "Rig crew contract does not mandate MPD well control training, "
            "creating competency gap for managed pressure operations."
        ),
        category=RiskCategory.RIG_CAPABILITY,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.HIGH,
        probability=0.45,
        risk_score=3 * 0.45,
        mitigation_owner="Contracts Manager",
        mitigation_action=(
            "Include IADC WellSharp MPD well control training requirement in "
            "rig contract; verify certificates before mobilisation."
        ),
        mpd_mitigation=True,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: MPD training not contractually "
            "required. Contracts Manager to insert IADC WellSharp clause and "
            "confirm crew certificates before rig mobilisation."
        ),
    ),
    WellPlanningRisk(
        risk_id="ST-008",
        title="Environmental permit for deepwater discharge",
        description=(
            "Discharge permit for synthetic mud cuttings in deepwater block "
            "not yet issued; may impose zero-discharge constraint."
        ),
        category=RiskCategory.REGULATORY,
        authority=RiskAuthority.STRATEGIC,
        severity=RiskSeverity.MEDIUM,
        probability=0.35,
        risk_score=2 * 0.35,
        mitigation_owner="HSSE Manager",
        mitigation_action=(
            "Engage environmental regulator early; model cuttings discharge "
            "footprint; budget cuttings-returns vessel as contingency."
        ),
        mpd_mitigation=False,
        escalation_template=(
            "ESCALATION REQUIRED — Strategic: Deepwater discharge permit not "
            "confirmed. HSSE Manager to file environmental application and "
            "confirm permit timeline vs spud date."
        ),
    ),
]
