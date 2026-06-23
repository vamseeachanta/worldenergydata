"""
ABOUTME: MPD configuration taxonomy and pressure window calculations.
ABOUTME: CBHP, PMCD, dual gradient, RFC configurations with ECD management.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MPDConfiguration:
    """Taxonomy record for a specific MPD configuration type."""

    config_type: str  # "CBHP" | "PMCD" | "dual_gradient" | "RFC"
    full_name: str
    description: str
    pressure_control: str
    typical_applications: list[str]
    key_equipment: list[str]
    advantages: list[str]
    limitations: list[str]


MPD_CONFIGURATIONS: list[MPDConfiguration] = [
    MPDConfiguration(
        config_type="CBHP",
        full_name="Constant Bottomhole Pressure",
        description=(
            "Maintains constant bottomhole pressure by applying variable "
            "surface back-pressure via a choke manifold while drilling."
        ),
        pressure_control=(
            "Surface back-pressure applied through automated choke system "
            "to compensate for ECD changes during connections and flow stops."
        ),
        typical_applications=[
            "Narrow pore-fracture pressure windows",
            "Deepwater wells with depleted formations",
            "HPHT wells requiring precise BHP control",
        ],
        key_equipment=[
            "Rotating Control Device (RCD)",
            "Automated choke manifold",
            "Back-pressure pump",
            "Real-time downhole pressure gauges",
        ],
        advantages=[
            "Eliminates ECD spikes during connections",
            "Reduces mud losses and well control incidents",
            "Enables drilling of otherwise undrillable wells",
        ],
        limitations=[
            "Requires RCD at surface — adds rig footprint",
            "Higher equipment cost vs conventional drilling",
        ],
    ),
    MPDConfiguration(
        config_type="PMCD",
        full_name="Pressurized Mud Cap Drilling",
        description=(
            "Seals the annulus at surface and uses a sacrificial fluid column "
            "to allow drilling without returns to surface, with annulus pressure control."
        ),
        pressure_control=(
            "Annulus pressurized at surface; sacrificial fluid pumped down "
            "annulus while returns are taken subsea or disposed downhole."
        ),
        typical_applications=[
            "Severe lost circulation formations",
            "Cavernous carbonates and vugular formations",
            "Deepwater subsea PMCD via mudlift pump",
        ],
        key_equipment=[
            "Rotating Control Device (RCD)",
            "Annulus pressure control choke",
            "Sacrificial fluid supply system",
            "Subsea mudlift pump (for subsea PMCD)",
        ],
        advantages=[
            "Enables drilling in total or near-total loss zones",
            "Avoids costly cement plugs and sidetracks",
            "Reduces NPT from lost circulation events",
        ],
        limitations=[
            "High sacrificial fluid costs",
            "Limited real-time formation evaluation while drilling",
        ],
    ),
    MPDConfiguration(
        config_type="dual_gradient",
        full_name="Dual Gradient Drilling",
        description=(
            "Uses two different fluid density gradients — seawater in the riser "
            "and heavier mud below the mudline — to decouple surface and BHP."
        ),
        pressure_control=(
            "Subsea mudlift pump removes mud from the seabed, replacing the "
            "riser fluid with seawater to approximate a gradient as if drilling "
            "from the mudline."
        ),
        typical_applications=[
            "Ultra-deepwater wells with narrow margins",
            "Subsalt formations with depleted sands",
            "Wells where conventional riser margin is insufficient",
        ],
        key_equipment=[
            "Subsea mudlift pump",
            "Subsea rotating control device",
            "Dual-gradient choke and kill lines",
            "Real-time subsea pressure gauges",
        ],
        advantages=[
            "Maximizes pressure window in ultra-deepwater",
            "Reduces equivalent mud weight at mudline",
            "Enables wells that are undrillable conventionally",
        ],
        limitations=[
            "Highest system complexity and cost",
            "Requires specialized subsea equipment",
            "Limited commercial deployments to date",
        ],
    ),
    MPDConfiguration(
        config_type="RFC",
        full_name="Returns Flow Control",
        description=(
            "Controls the flow of returns at surface using a choke system "
            "without full annulus pressurization; primarily manages ECD via flow rate control."
        ),
        pressure_control=(
            "Choke on returns line throttles flow to manage annular pressure "
            "indirectly via flow velocity and ECD adjustments."
        ),
        typical_applications=[
            "Shallow HPHT wells",
            "Land rig MPD applications",
            "Jack-up wells with moderate pressure challenges",
        ],
        key_equipment=[
            "Returns choke manifold",
            "Flow measurement instrumentation",
            "Passive or low-rating RCD",
        ],
        advantages=[
            "Lower cost and simpler than CBHP",
            "Easier rig-up on land and jackup rigs",
            "Effective for moderately narrow windows",
        ],
        limitations=[
            "Less precise BHP control than CBHP",
            "Not suitable for severe pressure window challenges",
        ],
    ),
]

_CONFIG_INDEX: dict[str, MPDConfiguration] = {
    c.config_type: c for c in MPD_CONFIGURATIONS
}


@dataclass
class PressureWindow:
    """Calculated pressure window and MPD requirement at a given depth."""

    depth_m: float
    pore_pressure_psi: float
    fracture_gradient_psi: float
    ecd_psi: float
    pressure_window_psi: float
    mpd_required: bool


class PressureWindowAnalyzer:
    """Calculates ECD and pressure window metrics for MPD applicability assessment."""

    _MUD_WEIGHT_PPG_TO_PSI_PER_FT: float = 0.052
    _M_TO_FT: float = 3.28084

    def analyze(
        self,
        depth_m: float,
        pore_pressure_psi: float,
        fracture_gradient_psi: float,
        mud_weight_ppg: float,
        flow_rate_gpm: float,
        annular_pressure_drop_psi: float = 200.0,
        threshold_psi: float = 200.0,
    ) -> PressureWindow:
        """Return a PressureWindow for the given well conditions.

        Args:
            depth_m: True vertical depth in metres.
            pore_pressure_psi: Formation pore pressure in psi.
            fracture_gradient_psi: Formation fracture gradient pressure in psi.
            mud_weight_ppg: Drilling fluid weight in pounds per gallon.
            flow_rate_gpm: Circulating flow rate in gallons per minute.
            annular_pressure_drop_psi: Annular friction pressure loss in psi.
            threshold_psi: Pressure window below which MPD is considered required.

        Returns:
            PressureWindow dataclass with calculated values.
        """
        ecd = self.ecd_pressure(mud_weight_ppg, depth_m, annular_pressure_drop_psi)
        window = fracture_gradient_psi - pore_pressure_psi
        required = self.mpd_required(window, threshold_psi)
        return PressureWindow(
            depth_m=depth_m,
            pore_pressure_psi=pore_pressure_psi,
            fracture_gradient_psi=fracture_gradient_psi,
            ecd_psi=ecd,
            pressure_window_psi=window,
            mpd_required=required,
        )

    def ecd_pressure(
        self,
        mud_weight_ppg: float,
        depth_m: float,
        annular_pressure_drop_psi: float,
    ) -> float:
        """Return equivalent circulating density pressure in psi.

        ECD pressure = hydrostatic mud pressure + annular friction pressure.

        Args:
            mud_weight_ppg: Mud weight in pounds per gallon.
            depth_m: Depth in metres.
            annular_pressure_drop_psi: Annular friction pressure loss in psi.
        """
        depth_ft = depth_m * self._M_TO_FT
        hydrostatic_psi = mud_weight_ppg * self._MUD_WEIGHT_PPG_TO_PSI_PER_FT * depth_ft
        return hydrostatic_psi + annular_pressure_drop_psi

    def mpd_required(
        self,
        pressure_window_psi: float,
        threshold_psi: float = 200.0,
    ) -> bool:
        """Return True when pressure window is narrower than threshold.

        Args:
            pressure_window_psi: Available pressure window in psi.
            threshold_psi: Minimum window before MPD is considered necessary.
        """
        return pressure_window_psi < threshold_psi


def get_configuration(config_type: str) -> MPDConfiguration:
    """Return the MPDConfiguration for the given config_type.

    Raises KeyError if config_type is not found.
    """
    if config_type not in _CONFIG_INDEX:
        raise KeyError(f"Unknown MPD config_type: {config_type!r}")
    return _CONFIG_INDEX[config_type]


def list_config_types() -> list[str]:
    """Return all available configuration type identifiers."""
    return list(_CONFIG_INDEX.keys())
