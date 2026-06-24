"""Buckskin field configuration — single source of truth for field metadata.

Defines blocks, BOEM lease numbers, operator history, and geological context
for the Buckskin development in Keathley Canyon, Gulf of Mexico.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class BuckskinConfig:
    """Immutable configuration for the Buckskin field."""

    field_name: str = "Buckskin"
    area_code: str = "KC"
    blocks: Tuple[int, ...] = (785, 828, 829, 830, 871, 872)
    geological_era: str = "Lower Tertiary / Wilcox"
    water_depth_ft: int = 6_800
    host_facility: str = "Lucius Spar"

    # BOEM OCS lease numbers (from BOEM serial register)
    # KC 871 and KC 872 share the same lease number OCS-G 25823
    boem_leases: Dict[str, str] = field(
        default_factory=lambda: {
            "OCS-G 25806": "KC 785",
            "OCS-G 25813": "KC 828",
            "OCS-G 25814": "KC 829",
            "OCS-G 25815": "KC 830",
            "OCS-G 25823": "KC 871 / KC 872",
        }
    )

    # Lease numbers as found in BSEE data (without "OCS-" prefix)
    # The data may use trimmed format like "G25806" or with space "G 25806"
    lease_numbers: Tuple[str, ...] = (
        "G25806",
        "G25813",
        "G25814",
        "G25815",
        "G25823",
    )

    # Additional leases discovered in BSEE LAB data (8 total)
    all_lease_numbers: Tuple[str, ...] = (
        "G19645",
        "G20979",
        "G25806",
        "G25813",
        "G25814",
        "G25815",
        "G25823",
        "G32650",
    )

    # Operator history (chronological)
    operator_history: Tuple[Tuple[str, int, str], ...] = (
        ("Repsol", 2009, "Discovery — KC 872 #1 via Stena Drillmax"),
        ("LLOG Exploration", 2018, "Development sanctioned, subsea tieback to Lucius"),
        ("LLOG Exploration", 2019, "First oil — ~30,000 bopd initial rate"),
        ("Harbour Energy", 2026, "Acquisition of LLOG assets including Buckskin"),
    )

    # Known benchmarks for validation
    expected_first_oil_year: int = 2019
    expected_peak_rate_bopd: int = 30_000
    discovery_well: str = "KC 872 #1 (Buckskin No 1)"
    discovery_td_ft: int = 29_404
    net_pay_ft: int = 400

    def block_set(self) -> set:
        """Return blocks as a set of both int and str forms."""
        s = set()
        for b in self.blocks:
            s.add(b)
            s.add(str(b))
        return s

    def lease_set(self) -> set:
        """Return all lease numbers as a set with common format variants."""
        s = set()
        for ln in self.all_lease_numbers:
            s.add(ln)
            # Also add with space: "G25806" -> "G 25806"
            if len(ln) > 1 and ln[0] == "G" and ln[1:].isdigit():
                s.add(f"G {ln[1:]}")
        return s


# Module-level singleton for convenience
BUCKSKIN = BuckskinConfig()
