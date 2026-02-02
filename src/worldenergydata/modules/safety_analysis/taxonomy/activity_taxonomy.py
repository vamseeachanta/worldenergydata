"""Energy Industry HSE Activity/Subactivity Taxonomy.

Hierarchical classification system for mapping HSE incidents to standardized
activities and subactivities across multiple data sources (BSEE, OSHA, USCG,
PHMSA, EPA TRI).

The taxonomy covers 14 top-level activities spanning upstream oil and gas,
marine transport, pipeline operations, and industrial safety domains.

Usage:
    from worldenergydata.modules.safety_analysis.taxonomy import ActivityTaxonomy
    taxonomy = ActivityTaxonomy()
    activity = taxonomy.get_activity("DRILL")
    all_activities = taxonomy.activities
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Subactivity:
    """A specific subactivity within a parent activity category."""

    code: str
    name: str
    description: str
    keywords: Tuple[str, ...] = ()


@dataclass(frozen=True)
class Activity:
    """A top-level HSE activity category with subactivities and source mappings."""

    code: str
    name: str
    description: str
    subactivities: Tuple[Subactivity, ...] = ()
    keywords: Tuple[str, ...] = ()
    naics_codes: Tuple[str, ...] = ()
    sic_codes: Tuple[str, ...] = ()
    bsee_accident_types: Tuple[str, ...] = ()
    marine_incident_types: Tuple[str, ...] = ()
    phmsa_cause_categories: Tuple[str, ...] = ()

    def get_subactivity(self, code: str) -> Optional[Subactivity]:
        """Get a subactivity by its code."""
        for sub in self.subactivities:
            return_val = sub if sub.code == code else None
            if return_val is not None:
                return return_val
        return None

    def list_subactivity_codes(self) -> List[str]:
        """Return all subactivity codes for this activity."""
        return [s.code for s in self.subactivities]


def _build_drilling_activity() -> Activity:
    """Build the DRILLING activity with subactivities."""
    return Activity(
        code="DRILL",
        name="Drilling",
        description="Well drilling, completion, workover, and well control operations",
        subactivities=(
            Subactivity(
                code="drilling_operations",
                name="Drilling Operations",
                description="Rotary drilling, directional drilling, spud operations",
                keywords=(
                    "drilling",
                    "drill",
                    "rotary",
                    "spud",
                    "kelly",
                    "top drive",
                    "mud pump",
                    "drill string",
                    "drill bit",
                    "directional",
                    "borehole",
                ),
            ),
            Subactivity(
                code="well_completion",
                name="Well Completion",
                description="Perforation, gravel pack, frac, completion operations",
                keywords=(
                    "completion",
                    "perforation",
                    "perforate",
                    "gravel pack",
                    "frac",
                    "fracturing",
                    "stimulation",
                    "acidizing",
                    "production tubing",
                    "packer",
                ),
            ),
            Subactivity(
                code="workover",
                name="Workover",
                description="Workover, well servicing, and remedial operations",
                keywords=(
                    "workover",
                    "work over",
                    "well servicing",
                    "remedial",
                    "sidetrack",
                    "recompletion",
                    "plug back",
                    "squeeze",
                ),
            ),
            Subactivity(
                code="well_control",
                name="Well Control",
                description="Blowout prevention, kick control, well kill",
                keywords=(
                    "blowout",
                    "blow out",
                    "bop",
                    "kick",
                    "well control",
                    "well kill",
                    "shut-in",
                    "choke",
                    "diverter",
                    "underground blowout",
                ),
            ),
            Subactivity(
                code="well_testing",
                name="Well Testing",
                description="Flow testing, well test, DST operations",
                keywords=(
                    "well test",
                    "flow test",
                    "dst",
                    "drill stem test",
                    "production test",
                    "pressure test",
                ),
            ),
            Subactivity(
                code="casing_cementing",
                name="Casing and Cementing",
                description="Casing running, cementing, and liner operations",
                keywords=(
                    "casing",
                    "cementing",
                    "cement",
                    "liner",
                    "casing run",
                    "shoe track",
                    "centralizer",
                ),
            ),
            Subactivity(
                code="tripping",
                name="Tripping",
                description="Tripping pipe in and out of hole",
                keywords=(
                    "tripping",
                    "trip in",
                    "trip out",
                    "pull out",
                    "run in",
                    "connection",
                    "stand",
                ),
            ),
            Subactivity(
                code="logging",
                name="Logging",
                description="Wireline logging, MWD/LWD operations",
                keywords=(
                    "logging",
                    "wireline",
                    "mwd",
                    "lwd",
                    "well log",
                    "caliper",
                    "gamma ray",
                ),
            ),
        ),
        keywords=(
            "drilling",
            "drill",
            "well",
            "rig",
            "derrick",
            "spud",
            "blowout",
            "bop",
            "casing",
            "completion",
            "workover",
        ),
        naics_codes=("211120", "213111"),
        sic_codes=("1311", "1381"),
        bsee_accident_types=("Blowout",),
        marine_incident_types=(),
        phmsa_cause_categories=(),
    )


def _build_production_activity() -> Activity:
    """Build the PRODUCTION activity with subactivities."""
    return Activity(
        code="PROD",
        name="Production",
        description="Hydrocarbon production, processing, and facility operations",
        subactivities=(
            Subactivity(
                code="production_operations",
                name="Production Operations",
                description="Facility production, wellhead operations, flow management",
                keywords=(
                    "production",
                    "producing",
                    "wellhead",
                    "flow",
                    "separator",
                    "treater",
                    "heater",
                    "tank battery",
                    "production platform",
                    "fpso",
                ),
            ),
            Subactivity(
                code="separation_processing",
                name="Separation and Processing",
                description="Oil/gas/water separation and processing",
                keywords=(
                    "separation",
                    "separator",
                    "processing",
                    "dehydration",
                    "sweetening",
                    "amine",
                    "glycol",
                    "gas plant",
                    "fractionation",
                ),
            ),
            Subactivity(
                code="compression",
                name="Compression",
                description="Gas compression and compressor operations",
                keywords=(
                    "compression",
                    "compressor",
                    "reciprocating",
                    "centrifugal compressor",
                    "gas lift",
                ),
            ),
            Subactivity(
                code="metering",
                name="Metering",
                description="Production metering and measurement",
                keywords=(
                    "metering",
                    "meter",
                    "measurement",
                    "lact",
                    "custody transfer",
                ),
            ),
            Subactivity(
                code="well_intervention",
                name="Well Intervention",
                description="Coiled tubing, slickline, and wireline intervention",
                keywords=(
                    "intervention",
                    "coiled tubing",
                    "slickline",
                    "wireline intervention",
                    "well intervention",
                ),
            ),
            Subactivity(
                code="artificial_lift",
                name="Artificial Lift",
                description="ESP, rod pump, gas lift systems",
                keywords=(
                    "artificial lift",
                    "esp",
                    "rod pump",
                    "sucker rod",
                    "gas lift",
                    "plunger lift",
                    "jet pump",
                ),
            ),
            Subactivity(
                code="chemical_injection",
                name="Chemical Injection",
                description="Chemical treatment and injection operations",
                keywords=(
                    "chemical injection",
                    "inhibitor",
                    "corrosion inhibitor",
                    "scale inhibitor",
                    "biocide",
                    "demulsifier",
                ),
            ),
        ),
        keywords=(
            "production",
            "producing",
            "separator",
            "processing",
            "compressor",
            "wellhead",
            "tank battery",
            "fpso",
        ),
        naics_codes=("211120", "211130"),
        sic_codes=("1311", "1382"),
        bsee_accident_types=(),
        marine_incident_types=(),
        phmsa_cause_categories=(),
    )


def _build_construction_activity() -> Activity:
    """Build the CONSTRUCTION_INSTALLATION activity with subactivities."""
    return Activity(
        code="CONST",
        name="Construction and Installation",
        description="Platform/facility construction, pipeline installation, decommissioning",
        subactivities=(
            Subactivity(
                code="platform_construction",
                name="Platform Construction",
                description="Offshore platform fabrication and installation",
                keywords=(
                    "platform construction",
                    "platform install",
                    "jacket",
                    "topsides",
                    "deck",
                    "fabrication",
                    "pile driving",
                    "structural",
                ),
            ),
            Subactivity(
                code="pipeline_installation",
                name="Pipeline Installation",
                description="Pipeline laying, tie-in, trenching operations",
                keywords=(
                    "pipeline install",
                    "pipe lay",
                    "pipelay",
                    "tie-in",
                    "trenching",
                    "pipeline construction",
                    "j-lay",
                    "s-lay",
                    "reel lay",
                ),
            ),
            Subactivity(
                code="subsea_installation",
                name="Subsea Installation",
                description="Subsea tree, manifold, jumper, and umbilical installation",
                keywords=(
                    "subsea install",
                    "subsea tree",
                    "manifold",
                    "jumper",
                    "umbilical",
                    "flowline",
                    "riser",
                ),
            ),
            Subactivity(
                code="hookup_commissioning",
                name="Hookup and Commissioning",
                description="Facility hookup, pre-commissioning, and commissioning",
                keywords=(
                    "hookup",
                    "commissioning",
                    "pre-commissioning",
                    "startup",
                    "start-up",
                    "energize",
                ),
            ),
            Subactivity(
                code="decommissioning",
                name="Decommissioning",
                description="Well P&A, platform removal, site clearance",
                keywords=(
                    "decommissioning",
                    "decommission",
                    "removal",
                    "plug and abandon",
                    "p&a",
                    "site clearance",
                    "salvage",
                    "demolition",
                ),
            ),
            Subactivity(
                code="heavy_lift",
                name="Heavy Lift",
                description="Heavy lift operations during construction/installation",
                keywords=(
                    "heavy lift",
                    "module lift",
                    "deck lift",
                    "float-over",
                    "derrick barge",
                ),
            ),
        ),
        keywords=(
            "construction",
            "installation",
            "fabrication",
            "decommission",
            "hookup",
            "commissioning",
            "platform",
            "jacket",
        ),
        naics_codes=("237120", "237310"),
        sic_codes=("1389", "1629"),
        bsee_accident_types=(),
        marine_incident_types=(),
        phmsa_cause_categories=("EXCAVATION DAMAGE",),
    )


def _build_marine_transport_activity() -> Activity:
    """Build the MARINE_TRANSPORT activity with subactivities."""
    return Activity(
        code="MARINE",
        name="Marine Transport",
        description="Vessel operations, navigation, cargo and personnel transfer",
        subactivities=(
            Subactivity(
                code="vessel_navigation",
                name="Vessel Navigation",
                description="Vessel operations, navigation, collision, grounding",
                keywords=(
                    "navigation",
                    "vessel",
                    "ship",
                    "boat",
                    "sailing",
                    "collision",
                    "allision",
                    "grounding",
                    "capsizing",
                    "foundering",
                    "sinking",
                ),
            ),
            Subactivity(
                code="cargo_transfer",
                name="Cargo Transfer",
                description="Cargo loading, offloading, and backloading",
                keywords=(
                    "cargo",
                    "loading",
                    "offloading",
                    "backloading",
                    "cargo transfer",
                    "supply boat",
                    "deck cargo",
                ),
            ),
            Subactivity(
                code="anchoring_mooring",
                name="Anchoring and Mooring",
                description="Anchor handling, mooring, and positioning",
                keywords=(
                    "anchor",
                    "anchoring",
                    "mooring",
                    "bollard",
                    "hawser",
                    "anchor handling",
                    "positioning",
                    "dynamic positioning",
                    "dp",
                ),
            ),
            Subactivity(
                code="towing",
                name="Towing",
                description="Towing operations and barge transport",
                keywords=(
                    "towing",
                    "tow",
                    "barge",
                    "tug",
                    "towline",
                ),
            ),
            Subactivity(
                code="passenger_transfer",
                name="Passenger Transfer",
                description="Personnel transfer by boat, basket, or gangway",
                keywords=(
                    "passenger",
                    "personnel transfer",
                    "crew boat",
                    "swing rope",
                    "billy pugh",
                    "gangway",
                    "walk to work",
                ),
            ),
            Subactivity(
                code="vessel_maintenance",
                name="Vessel Maintenance",
                description="Vessel maintenance, drydock, and repair",
                keywords=(
                    "vessel maintenance",
                    "drydock",
                    "hull",
                    "engine room",
                    "marine engine",
                ),
            ),
        ),
        keywords=(
            "vessel",
            "ship",
            "boat",
            "marine",
            "maritime",
            "navigation",
            "collision",
            "grounding",
            "capsizing",
            "towing",
            "barge",
        ),
        naics_codes=("483111", "483211", "488330"),
        sic_codes=("4412", "4424", "4492"),
        bsee_accident_types=("Collision",),
        marine_incident_types=(
            "COLLISION",
            "CAPSIZING",
            "GROUNDING",
            "FLOODING",
        ),
        phmsa_cause_categories=(),
    )


def _build_pipeline_operations_activity() -> Activity:
    """Build the PIPELINE_OPERATIONS activity with subactivities."""
    return Activity(
        code="PIPE",
        name="Pipeline Operations",
        description="Pipeline transport, inspection, maintenance, and integrity management",
        subactivities=(
            Subactivity(
                code="pipeline_transport",
                name="Pipeline Transport",
                description="Oil/gas pipeline transport operations",
                keywords=(
                    "pipeline transport",
                    "pipeline operation",
                    "pipeline flow",
                    "pipeline pressure",
                    "pipeline rupture",
                    "pipeline leak",
                ),
            ),
            Subactivity(
                code="pigging",
                name="Pigging",
                description="Pipeline pigging and intelligent pigging",
                keywords=(
                    "pigging",
                    "pig",
                    "pig run",
                    "intelligent pig",
                    "inline inspection",
                    "ili",
                ),
            ),
            Subactivity(
                code="pipeline_inspection",
                name="Pipeline Inspection",
                description="Pipeline inspection, survey, and integrity assessment",
                keywords=(
                    "pipeline inspection",
                    "pipeline survey",
                    "integrity assessment",
                    "cathodic protection",
                    "pipeline integrity",
                    "anomaly",
                ),
            ),
            Subactivity(
                code="pipeline_repair",
                name="Pipeline Repair",
                description="Pipeline repair, clamp, sleeve, and hot tap",
                keywords=(
                    "pipeline repair",
                    "clamp",
                    "sleeve",
                    "hot tap",
                    "composite repair",
                    "weld repair",
                ),
            ),
            Subactivity(
                code="valve_operations",
                name="Valve Operations",
                description="Pipeline valve operation and maintenance",
                keywords=(
                    "valve",
                    "block valve",
                    "check valve",
                    "emergency shutdown",
                    "esd",
                    "valve operation",
                ),
            ),
            Subactivity(
                code="metering_stations",
                name="Metering Stations",
                description="Pipeline metering and compressor station operations",
                keywords=(
                    "metering station",
                    "compressor station",
                    "pump station",
                    "terminal",
                ),
            ),
        ),
        keywords=(
            "pipeline",
            "pipe",
            "pigging",
            "pig",
            "valve",
            "metering station",
            "compressor station",
        ),
        naics_codes=("486110", "486210", "486910"),
        sic_codes=("4612", "4613", "4619"),
        bsee_accident_types=(),
        marine_incident_types=(),
        phmsa_cause_categories=(
            "CORROSION",
            "EQUIPMENT FAILURE",
            "EXCAVATION DAMAGE",
            "INCORRECT OPERATION",
            "MATERIAL FAILURE OF PIPE OR WELD",
            "NATURAL FORCE DAMAGE",
            "OTHER OUTSIDE FORCE DAMAGE",
            "ALL OTHER CAUSES",
        ),
    )


def _build_diving_activity() -> Activity:
    """Build the DIVING activity with subactivities."""
    return Activity(
        code="DIVE",
        name="Diving",
        description="Commercial diving, ROV, and subsea operations",
        subactivities=(
            Subactivity(
                code="saturation_diving",
                name="Saturation Diving",
                description="Saturation diving operations",
                keywords=(
                    "saturation diving",
                    "sat diving",
                    "sat diver",
                    "diving bell",
                    "chamber",
                ),
            ),
            Subactivity(
                code="surface_supplied",
                name="Surface Supplied Diving",
                description="Surface-supplied diving operations",
                keywords=(
                    "surface supplied",
                    "surface diving",
                    "air diving",
                    "diver",
                    "diving",
                    "dive",
                ),
            ),
            Subactivity(
                code="rov_operations",
                name="ROV Operations",
                description="Remotely operated vehicle operations",
                keywords=(
                    "rov",
                    "remotely operated",
                    "underwater vehicle",
                    "rov operation",
                ),
            ),
            Subactivity(
                code="subsea_inspection",
                name="Subsea Inspection",
                description="Subsea inspection and survey by diver or ROV",
                keywords=(
                    "subsea inspection",
                    "underwater inspection",
                    "subsea survey",
                ),
            ),
            Subactivity(
                code="subsea_repair",
                name="Subsea Repair",
                description="Subsea repair and maintenance operations",
                keywords=(
                    "subsea repair",
                    "underwater repair",
                    "subsea maintenance",
                    "hyperbaric welding",
                ),
            ),
        ),
        keywords=(
            "diving",
            "diver",
            "dive",
            "subsea",
            "rov",
            "saturation",
            "underwater",
        ),
        naics_codes=("213112",),
        sic_codes=("1389",),
        bsee_accident_types=(),
        marine_incident_types=(),
        phmsa_cause_categories=(),
    )


def _build_crane_lifting_activity() -> Activity:
    """Build the CRANE_LIFTING activity with subactivities."""
    return Activity(
        code="CRANE",
        name="Crane and Lifting",
        description="Crane operations, rigging, personnel transfer, and cargo handling",
        subactivities=(
            Subactivity(
                code="crane_operations",
                name="Crane Operations",
                description="Pedestal crane, mobile crane, and crawler crane operations",
                keywords=(
                    "crane",
                    "crane operation",
                    "pedestal crane",
                    "mobile crane",
                    "crawler crane",
                    "boom",
                    "crane incident",
                    "crane accident",
                ),
            ),
            Subactivity(
                code="rigging",
                name="Rigging",
                description="Rigging, sling, and load handling",
                keywords=(
                    "rigging",
                    "sling",
                    "shackle",
                    "rigger",
                    "load handling",
                ),
            ),
            Subactivity(
                code="personnel_transfer",
                name="Personnel Transfer by Crane",
                description="Personnel basket, man-riding, and crane transfers",
                keywords=(
                    "personnel basket",
                    "man-riding",
                    "personnel lift",
                    "man basket",
                ),
            ),
            Subactivity(
                code="cargo_handling",
                name="Cargo Handling",
                description="Container and cargo lifting operations",
                keywords=(
                    "cargo handling",
                    "container",
                    "cargo lift",
                    "cargo basket",
                    "deck handling",
                ),
            ),
            Subactivity(
                code="heavy_lift",
                name="Heavy Lift",
                description="Heavy and critical lift operations",
                keywords=(
                    "heavy lift",
                    "critical lift",
                    "tandem lift",
                    "module lift",
                ),
            ),
        ),
        keywords=(
            "crane",
            "lifting",
            "hoist",
            "rigging",
            "sling",
            "boom",
            "winch",
        ),
        naics_codes=("238990",),
        sic_codes=("1794",),
        bsee_accident_types=("Crane", "Other Lifting Device"),
        marine_incident_types=(),
        phmsa_cause_categories=(),
    )


def _build_maintenance_activity() -> Activity:
    """Build the MAINTENANCE activity with subactivities."""
    return Activity(
        code="MAINT",
        name="Maintenance",
        description="Facility and equipment maintenance, turnaround, and inspection",
        subactivities=(
            Subactivity(
                code="preventive_maintenance",
                name="Preventive Maintenance",
                description="Scheduled preventive maintenance activities",
                keywords=(
                    "preventive maintenance",
                    "pm",
                    "scheduled maintenance",
                    "routine maintenance",
                ),
            ),
            Subactivity(
                code="corrective_maintenance",
                name="Corrective Maintenance",
                description="Breakdown and corrective maintenance",
                keywords=(
                    "corrective maintenance",
                    "breakdown",
                    "repair",
                    "fix",
                    "troubleshoot",
                ),
            ),
            Subactivity(
                code="turnaround_shutdown",
                name="Turnaround and Shutdown",
                description="Facility turnaround, shutdown, and outage operations",
                keywords=(
                    "turnaround",
                    "shutdown",
                    "outage",
                    "tar",
                    "planned shutdown",
                ),
            ),
            Subactivity(
                code="inspection_testing",
                name="Inspection and Testing",
                description="Equipment inspection, NDT, and pressure testing",
                keywords=(
                    "inspection",
                    "ndt",
                    "non-destructive",
                    "pressure test",
                    "hydrostatic",
                    "radiography",
                    "ultrasonic",
                    "magnetic particle",
                ),
            ),
            Subactivity(
                code="painting_coating",
                name="Painting and Coating",
                description="Surface preparation, painting, and coating operations",
                keywords=(
                    "painting",
                    "coating",
                    "sandblasting",
                    "surface preparation",
                    "corrosion protection",
                ),
            ),
        ),
        keywords=(
            "maintenance",
            "repair",
            "turnaround",
            "shutdown",
            "inspection",
            "overhaul",
        ),
        naics_codes=("811310",),
        sic_codes=("7699",),
        bsee_accident_types=(),
        marine_incident_types=(),
        phmsa_cause_categories=(),
    )


def _build_environmental_activity() -> Activity:
    """Build the ENVIRONMENTAL activity with subactivities."""
    return Activity(
        code="ENV",
        name="Environmental",
        description="Environmental releases, pollution, spills, and compliance",
        subactivities=(
            Subactivity(
                code="oil_spill",
                name="Oil Spill",
                description="Oil spills, hydrocarbon releases to water or land",
                keywords=(
                    "oil spill",
                    "spill",
                    "hydrocarbon release",
                    "oil discharge",
                    "sheen",
                    "oil on water",
                ),
            ),
            Subactivity(
                code="chemical_release",
                name="Chemical Release",
                description="Chemical releases and toxic substance discharges",
                keywords=(
                    "chemical release",
                    "chemical spill",
                    "toxic release",
                    "hazardous material",
                    "hazmat",
                    "tri release",
                ),
            ),
            Subactivity(
                code="gas_release",
                name="Gas Release",
                description="Uncontrolled gas releases and venting",
                keywords=(
                    "gas release",
                    "gas leak",
                    "venting",
                    "flaring",
                    "fugitive emission",
                    "methane",
                    "h2s release",
                    "shutdown from gas release",
                ),
            ),
            Subactivity(
                code="waste_management",
                name="Waste Management",
                description="Waste disposal, treatment, and management",
                keywords=(
                    "waste",
                    "disposal",
                    "treatment",
                    "effluent",
                    "produced water",
                    "drill cuttings",
                ),
            ),
            Subactivity(
                code="emissions",
                name="Emissions",
                description="Air emissions, flaring, and greenhouse gas releases",
                keywords=(
                    "emission",
                    "flare",
                    "greenhouse gas",
                    "ghg",
                    "sox",
                    "nox",
                    "voc",
                    "particulate",
                ),
            ),
        ),
        keywords=(
            "pollution",
            "spill",
            "release",
            "emission",
            "environmental",
            "discharge",
            "contamination",
        ),
        naics_codes=("562910",),
        sic_codes=("4959",),
        bsee_accident_types=("Pollution",),
        marine_incident_types=("POLLUTION",),
        phmsa_cause_categories=(),
    )


def _build_electrical_activity() -> Activity:
    """Build the ELECTRICAL activity with subactivities."""
    return Activity(
        code="ELEC",
        name="Electrical",
        description="Electrical systems, power generation, and electrical maintenance",
        subactivities=(
            Subactivity(
                code="electrical_maintenance",
                name="Electrical Maintenance",
                description="Electrical system maintenance and repair",
                keywords=(
                    "electrical maintenance",
                    "electrical repair",
                    "wiring",
                    "cable",
                    "electrical work",
                ),
            ),
            Subactivity(
                code="power_generation",
                name="Power Generation",
                description="Generator, turbine, and power generation operations",
                keywords=(
                    "power generation",
                    "generator",
                    "turbine",
                    "power plant",
                    "power supply",
                ),
            ),
            Subactivity(
                code="switchgear",
                name="Switchgear",
                description="Switchgear, transformer, and distribution operations",
                keywords=(
                    "switchgear",
                    "transformer",
                    "distribution",
                    "circuit breaker",
                    "bus bar",
                ),
            ),
            Subactivity(
                code="lighting",
                name="Lighting",
                description="Lighting systems and maintenance",
                keywords=(
                    "lighting",
                    "light",
                    "illumination",
                ),
            ),
            Subactivity(
                code="grounding",
                name="Grounding",
                description="Electrical grounding and bonding",
                keywords=(
                    "grounding",
                    "earthing",
                    "bonding",
                    "static discharge",
                ),
            ),
        ),
        keywords=(
            "electrical",
            "electric",
            "electrocute",
            "power",
            "generator",
            "switchgear",
            "voltage",
            "arc flash",
        ),
        naics_codes=("238210",),
        sic_codes=("1731",),
        bsee_accident_types=(),
        marine_incident_types=(),
        phmsa_cause_categories=(),
    )


def _build_process_safety_activity() -> Activity:
    """Build the PROCESS_SAFETY activity with subactivities."""
    return Activity(
        code="PSAFE",
        name="Process Safety",
        description="Process safety management events, fires, explosions, and equipment failures",
        subactivities=(
            Subactivity(
                code="pressure_release",
                name="Pressure Release",
                description="Unplanned pressure releases, relief valve activations",
                keywords=(
                    "pressure release",
                    "overpressure",
                    "relief valve",
                    "psv",
                    "pressure safety",
                    "rupture",
                    "loss of containment",
                    "loc",
                ),
            ),
            Subactivity(
                code="equipment_failure",
                name="Equipment Failure",
                description="Major equipment failure or malfunction",
                keywords=(
                    "equipment failure",
                    "equipment malfunction",
                    "mechanical failure",
                    "structural failure",
                    "fatigue failure",
                    "corrosion failure",
                ),
            ),
            Subactivity(
                code="instrument_failure",
                name="Instrument Failure",
                description="Instrument, sensor, or control system failure",
                keywords=(
                    "instrument failure",
                    "sensor failure",
                    "transmitter",
                    "gauge",
                    "instrument malfunction",
                ),
            ),
            Subactivity(
                code="control_system",
                name="Control System",
                description="Control system, DCS, SCADA, and safety system events",
                keywords=(
                    "control system",
                    "dcs",
                    "scada",
                    "plc",
                    "safety system",
                    "sil",
                    "sis",
                    "emergency shutdown",
                    "esd",
                ),
            ),
            Subactivity(
                code="fire_explosion",
                name="Fire and Explosion",
                description="Fire, explosion, and ignition events",
                keywords=(
                    "fire",
                    "explosion",
                    "ignition",
                    "deflagration",
                    "detonation",
                    "flash fire",
                    "fireball",
                    "combustion",
                    "burn",
                ),
            ),
        ),
        keywords=(
            "fire",
            "explosion",
            "process safety",
            "overpressure",
            "loss of containment",
            "equipment failure",
            "ignition",
        ),
        naics_codes=(),
        sic_codes=(),
        bsee_accident_types=(
            "Fire",
            "Explosion",
            "Shutdown from Gas Release",
        ),
        marine_incident_types=("FIRE", "EXPLOSION"),
        phmsa_cause_categories=("EQUIPMENT FAILURE",),
    )


def _build_personnel_safety_activity() -> Activity:
    """Build the PERSONNEL_SAFETY activity with subactivities."""
    return Activity(
        code="PERS",
        name="Personnel Safety",
        description="Occupational health, personal safety, and injury events",
        subactivities=(
            Subactivity(
                code="slip_trip_fall",
                name="Slip, Trip, and Fall",
                description="Slip, trip, and same-level fall incidents",
                keywords=(
                    "slip",
                    "trip",
                    "slippery",
                    "stumble",
                    "lost balance",
                ),
            ),
            Subactivity(
                code="struck_by",
                name="Struck By",
                description="Struck by object, dropped object, or impact injuries",
                keywords=(
                    "struck by",
                    "hit by",
                    "dropped object",
                    "falling object",
                    "impact",
                    "struck",
                ),
            ),
            Subactivity(
                code="caught_between",
                name="Caught Between",
                description="Caught in, caught between, or pinch point injuries",
                keywords=(
                    "caught between",
                    "caught in",
                    "pinch point",
                    "crush",
                    "crushed",
                    "entangle",
                    "entrap",
                ),
            ),
            Subactivity(
                code="confined_space",
                name="Confined Space",
                description="Confined space entry and related incidents",
                keywords=(
                    "confined space",
                    "enclosed space",
                    "tank entry",
                    "vessel entry",
                    "permit space",
                ),
            ),
            Subactivity(
                code="heat_stress",
                name="Heat Stress",
                description="Heat stress, heat exhaustion, and heat stroke",
                keywords=(
                    "heat stress",
                    "heat exhaustion",
                    "heat stroke",
                    "hyperthermia",
                    "dehydration",
                ),
            ),
            Subactivity(
                code="h2s_exposure",
                name="H2S Exposure",
                description="Hydrogen sulfide exposure incidents",
                keywords=(
                    "h2s",
                    "hydrogen sulfide",
                    "sour gas",
                    "h2s exposure",
                ),
            ),
            Subactivity(
                code="fall_from_height",
                name="Fall from Height",
                description="Falls from elevation, scaffolding, ladders",
                keywords=(
                    "fall",
                    "fell",
                    "fall from height",
                    "fall from elevation",
                    "scaffolding",
                    "scaffold",
                    "ladder",
                    "roof",
                    "fall protection",
                ),
            ),
        ),
        keywords=(
            "injury",
            "hurt",
            "lta",
            "rw/jt",
            "first aid",
            "medical treatment",
            "fatality",
            "slip",
            "trip",
            "fall",
            "fell",
            "struck",
            "caught",
            "crush",
        ),
        naics_codes=(),
        sic_codes=(),
        bsee_accident_types=(
            "Injury",
            "LTA",
            "RW/JT",
            "Fatality",
            "Other Injury",
        ),
        marine_incident_types=("PERSONNEL_INJURY",),
        phmsa_cause_categories=(),
    )


def _build_helicopter_activity() -> Activity:
    """Build the HELICOPTER activity with subactivities."""
    return Activity(
        code="HELI",
        name="Helicopter",
        description="Aviation and helicopter transport operations",
        subactivities=(
            Subactivity(
                code="helicopter_transport",
                name="Helicopter Transport",
                description="Helicopter passenger and cargo transport",
                keywords=(
                    "helicopter",
                    "chopper",
                    "helo",
                    "flight",
                    "aviation",
                    "aircraft",
                    "pilot",
                ),
            ),
            Subactivity(
                code="helideck_operations",
                name="Helideck Operations",
                description="Helideck, landing, refueling operations",
                keywords=(
                    "helideck",
                    "helipad",
                    "landing",
                    "refuel",
                    "helicopter landing",
                ),
            ),
        ),
        keywords=(
            "helicopter",
            "aviation",
            "helideck",
            "flight",
            "aircraft",
        ),
        naics_codes=("481211",),
        sic_codes=("4522",),
        bsee_accident_types=(),
        marine_incident_types=(),
        phmsa_cause_categories=(),
    )


def _build_other_activity() -> Activity:
    """Build the OTHER activity with subactivities."""
    return Activity(
        code="OTHER",
        name="Other",
        description="Unclassified or miscellaneous activities",
        subactivities=(
            Subactivity(
                code="other",
                name="Other",
                description="Other unclassified activity",
                keywords=(),
            ),
            Subactivity(
                code="unknown",
                name="Unknown",
                description="Activity could not be determined",
                keywords=(),
            ),
        ),
        keywords=(),
        naics_codes=(),
        sic_codes=(),
        bsee_accident_types=(),
        marine_incident_types=("OTHER",),
        phmsa_cause_categories=("ALL OTHER CAUSES",),
    )


class ActivityTaxonomy:
    """Registry of all HSE activities and their subactivities.

    Provides lookup by code, keyword search, and source-specific
    field mapping for cross-source incident classification.
    """

    def __init__(self) -> None:
        self._activities: Tuple[Activity, ...] = (
            _build_drilling_activity(),
            _build_production_activity(),
            _build_construction_activity(),
            _build_marine_transport_activity(),
            _build_pipeline_operations_activity(),
            _build_diving_activity(),
            _build_crane_lifting_activity(),
            _build_maintenance_activity(),
            _build_environmental_activity(),
            _build_electrical_activity(),
            _build_process_safety_activity(),
            _build_personnel_safety_activity(),
            _build_helicopter_activity(),
            _build_other_activity(),
        )
        self._code_index: Dict[str, Activity] = {a.code: a for a in self._activities}
        self._bsee_index = self._build_bsee_index()
        self._marine_index = self._build_marine_index()
        self._phmsa_index = self._build_phmsa_index()
        self._sic_index = self._build_sic_index()
        self._naics_index = self._build_naics_index()

    @property
    def activities(self) -> Tuple[Activity, ...]:
        """Return all registered activities."""
        return self._activities

    def get_activity(self, code: str) -> Optional[Activity]:
        """Get an activity by its code."""
        return self._code_index.get(code)

    def get_activity_codes(self) -> List[str]:
        """Return all activity codes."""
        return list(self._code_index.keys())

    def find_by_bsee_type(self, accident_type: str) -> Optional[Activity]:
        """Find activity matching a BSEE ACCIDENT_TYPE value.

        Matches against known BSEE accident type strings, using
        case-insensitive substring matching for the composite
        BSEE type format (e.g. '- Fire - Pollution').

        For composite types (multiple categories separated by ' - '),
        the first matching segment takes priority. This ensures that
        e.g. 'Fire - Pollution' maps to PSAFE (fire) not ENV (pollution).
        """
        normalized = accident_type.strip().strip("-").strip().lower()
        # Split composite BSEE types on ' - ' delimiter
        segments = [s.strip() for s in normalized.split("-") if s.strip()]
        # Check each segment in order for a match
        for segment in segments:
            for key, activity in self._bsee_index.items():
                if key in segment:
                    return activity
        # Fallback: check entire string
        for key, activity in self._bsee_index.items():
            if key in normalized:
                return activity
        return None

    def find_by_marine_type(self, incident_type: str) -> Optional[Activity]:
        """Find activity matching a marine_safety incident_type value."""
        normalized = incident_type.strip().upper()
        return self._marine_index.get(normalized)

    def find_by_phmsa_cause(self, cause_category: str) -> Optional[Activity]:
        """Find activity matching a PHMSA cause category."""
        normalized = cause_category.strip().upper()
        return self._phmsa_index.get(normalized)

    def find_by_sic_code(self, sic_code: str) -> Optional[Activity]:
        """Find activity matching a SIC code prefix."""
        sic_str = str(sic_code).strip()
        for prefix, activity in self._sic_index.items():
            if sic_str.startswith(prefix):
                return activity
        return None

    def find_by_naics_code(self, naics_code: str) -> Optional[Activity]:
        """Find activity matching a NAICS code prefix."""
        naics_str = str(naics_code).strip()
        for prefix, activity in self._naics_index.items():
            if naics_str.startswith(prefix):
                return activity
        return None

    def _build_bsee_index(self) -> Dict[str, Activity]:
        """Build lookup from BSEE accident type substring to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for bsee_type in activity.bsee_accident_types:
                index[bsee_type.lower()] = activity
        return index

    def _build_marine_index(self) -> Dict[str, Activity]:
        """Build lookup from marine incident type to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for marine_type in activity.marine_incident_types:
                index[marine_type.upper()] = activity
        return index

    def _build_phmsa_index(self) -> Dict[str, Activity]:
        """Build lookup from PHMSA cause category to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for cause in activity.phmsa_cause_categories:
                index[cause.upper()] = activity
        return index

    def _build_sic_index(self) -> Dict[str, Activity]:
        """Build lookup from SIC code prefix to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for sic in activity.sic_codes:
                index[sic] = activity
        return index

    def _build_naics_index(self) -> Dict[str, Activity]:
        """Build lookup from NAICS code prefix to activity."""
        index: Dict[str, Activity] = {}
        for activity in self._activities:
            for naics in activity.naics_codes:
                index[naics] = activity
        return index

    def summary(self) -> Dict[str, int]:
        """Return summary of activity codes and subactivity counts."""
        return {a.code: len(a.subactivities) for a in self._activities}
