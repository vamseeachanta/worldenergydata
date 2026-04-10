# ABOUTME: Canadian Unique Well Identifier (UWI) parser for DLS and NTS survey systems.
# ABOUTME: Parses, validates, formats, and normalizes UWI strings across Canadian provinces.

"""
Canadian UWI (Unique Well Identifier) Parser.

Supports two survey systems used in Canada:
1. DLS (Dominion Land Survey) - Used in Alberta, Saskatchewan, Manitoba
   Format: LSS.LL-SS-TTT-RRWM.EE
   Example: 100.16-09-010-09W4.00

2. NTS (National Topographic System) - Used in BC, Yukon, NWT
   Format: LSS.A-XX-Y-ZZZ-A-NN.EE
   Example: 200.A-001-B-094-A-01.00

UWI Components:
- Location Exception (LSS): 3 digits, identifies unique location
- Legal Subdivision (LL): For DLS, 2 digits (01-16)
- Section (SS): 2 digits (01-36 for DLS)
- Township (TTT): 3 digits
- Range (RR): 2 digits
- Meridian (WM): W followed by meridian number (1-6 for DLS)
- Event Sequence (EE): 2 digits, tracks well events

References:
- AER Directive 059: Well Drilling and Completion Data Filing Requirements
- CAPP Well Naming Convention
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class UWISurveySystem(Enum):
    """Survey systems used for Canadian UWIs."""

    DLS = "DLS"  # Dominion Land Survey (AB, SK, MB)
    NTS = "NTS"  # National Topographic System (BC, YT, NT)
    UNKNOWN = "UNKNOWN"


class UWIParseError(Exception):
    """Exception raised when UWI parsing fails."""

    def __init__(self, message: str, uwi: str, detail: Optional[str] = None):
        self.message = message
        self.uwi = uwi
        self.detail = detail
        super().__init__(f"{message}: '{uwi}'" + (f" ({detail})" if detail else ""))


@dataclass
class UWIComponents:
    """
    Parsed components of a Canadian Unique Well Identifier.

    Attributes:
        survey_system: The survey system (DLS or NTS)
        location_exception: Location exception code (3 digits)
        legal_subdivision: Legal subdivision (2 digits for DLS, letter+digits for NTS)
        section: Section number (2 digits)
        township: Township number (3 digits for DLS, map area for NTS)
        range: Range number (2 digits for DLS, map sheet for NTS)
        meridian: Meridian indicator (e.g., "W4" for DLS)
        event_sequence: Event sequence number (2 digits)
        raw_uwi: Original UWI string as provided
        normalized_uwi: UWI in standard normalized format

        NTS-specific fields:
        quarter_unit: Quarter unit letter (A-D) for NTS
        unit: Unit number for NTS
        block: Block letter for NTS
        map_area: Map area code for NTS
        map_sheet: Map sheet identifier for NTS
    """

    survey_system: UWISurveySystem
    location_exception: str
    legal_subdivision: str
    section: str
    township: str
    range: str
    meridian: str
    event_sequence: str
    raw_uwi: str
    normalized_uwi: str = ""

    # NTS-specific fields (optional)
    quarter_unit: Optional[str] = None
    unit: Optional[str] = None
    block: Optional[str] = None
    map_area: Optional[str] = None
    map_sheet: Optional[str] = None

    # Metadata
    province: Optional[str] = None
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert components to dictionary."""
        return {
            "survey_system": self.survey_system.value,
            "location_exception": self.location_exception,
            "legal_subdivision": self.legal_subdivision,
            "section": self.section,
            "township": self.township,
            "range": self.range,
            "meridian": self.meridian,
            "event_sequence": self.event_sequence,
            "raw_uwi": self.raw_uwi,
            "normalized_uwi": self.normalized_uwi,
            "quarter_unit": self.quarter_unit,
            "unit": self.unit,
            "block": self.block,
            "map_area": self.map_area,
            "map_sheet": self.map_sheet,
            "province": self.province,
            "is_valid": self.is_valid,
            "validation_errors": self.validation_errors,
        }


class UWIParser:
    """
    Parser for Canadian Unique Well Identifiers (UWIs).

    Supports both DLS (Dominion Land Survey) and NTS (National Topographic System)
    formats used across Canadian provinces.

    Example:
        parser = UWIParser()

        # Parse a DLS UWI (Alberta)
        components = parser.parse("100.16-09-010-09W4.00")
        logger.info(components.survey_system)  # UWISurveySystem.DLS

        # Validate a UWI
        is_valid, error = parser.validate("100.16-09-010-09W4.00")
        logger.info(f"Valid: {is_valid}")

        # Normalize a UWI
        normalized = parser.normalize("100/16-09-010-09W4/00")
        logger.info(normalized)  # 100.16-09-010-09W4.00
    """

    # DLS format pattern
    # Format: LSS.LL-SS-TTT-RRWM.EE
    # Example: 100.16-09-010-09W4.00
    DLS_PATTERN = re.compile(
        r"^(?P<location_exception>\d{3})"  # Location exception (3 digits)
        r"[./]"  # Separator (period or slash)
        r"(?P<legal_subdivision>\d{2})"  # Legal subdivision (2 digits, 01-16)
        r"[-/]"  # Separator
        r"(?P<section>\d{2})"  # Section (2 digits, 01-36)
        r"[-/]"  # Separator
        r"(?P<township>\d{3})"  # Township (3 digits)
        r"[-/]"  # Separator
        r"(?P<range>\d{2})"  # Range (2 digits)
        r"(?P<meridian>W\d)"  # Meridian (W followed by 1-6)
        r"[./]"  # Separator
        r"(?P<event_sequence>\d{2})$",  # Event sequence (2 digits)
        re.IGNORECASE,
    )

    # Alternative DLS pattern without separators (compact format)
    DLS_COMPACT_PATTERN = re.compile(
        r"^(?P<location_exception>\d{3})"
        r"(?P<legal_subdivision>\d{2})"
        r"(?P<section>\d{2})"
        r"(?P<township>\d{3})"
        r"(?P<range>\d{2})"
        r"(?P<meridian>W\d)"
        r"(?P<event_sequence>\d{2})$",
        re.IGNORECASE,
    )

    # NTS format pattern
    # Format: LSS.A-XXX-Y-ZZZ-A-NN.EE
    # Example: 200.A-001-B-094-A-01.00
    NTS_PATTERN = re.compile(
        r"^(?P<location_exception>\d{3})"  # Location exception (3 digits)
        r"[./]"  # Separator
        r"(?P<quarter_unit>[A-D])"  # Quarter unit (A-D)
        r"[-/]"  # Separator
        r"(?P<unit>\d{3})"  # Unit (3 digits)
        r"[-/]"  # Separator
        r"(?P<block>[A-L])"  # Block (A-L)
        r"[-/]"  # Separator
        r"(?P<map_area>\d{3})"  # Map area (3 digits)
        r"[-/]"  # Separator
        r"(?P<map_sheet>[A-P])"  # Map sheet (A-P)
        r"[-/]"  # Separator
        r"(?P<map_subsheet>\d{2})"  # Map subsheet (2 digits)
        r"[./]"  # Separator
        r"(?P<event_sequence>\d{2})$",  # Event sequence (2 digits)
        re.IGNORECASE,
    )

    # Simplified NTS pattern (commonly used format)
    NTS_SIMPLE_PATTERN = re.compile(
        r"^(?P<location_exception>\d{3})"  # Location exception
        r"[./]"
        r"(?P<quarter_unit>[A-Da-d])"  # Quarter unit
        r"[-/]"
        r"(?P<unit>\d{1,3})"  # Unit (1-3 digits)
        r"[-/]"
        r"(?P<block>[A-La-l])"  # Block
        r"[-/]"
        r"(?P<map_area>\d{2,3})"  # Map area (2-3 digits)
        r"[-/]?"
        r"(?P<map_sheet>[A-Pa-p])?"  # Optional map sheet
        r"[-/]?"
        r"(?P<map_subsheet>\d{1,2})?"  # Optional map subsheet
        r"[./]"
        r"(?P<event_sequence>\d{2})$",
        re.IGNORECASE,
    )

    # Valid ranges for DLS components
    DLS_VALID_RANGES = {
        "legal_subdivision": (1, 16),  # LSD 1-16
        "section": (1, 36),  # Section 1-36
        "township": (1, 126),  # Township 1-126
        "range": (1, 34),  # Range 1-34 (varies by meridian)
        "meridian": (1, 6),  # Meridian W1-W6
    }

    # Province to meridian mapping for DLS
    MERIDIAN_PROVINCES = {
        "W1": ["MB"],  # First Meridian - Manitoba
        "W2": ["SK", "MB"],  # Second Meridian - Saskatchewan, Manitoba
        "W3": ["SK", "AB"],  # Third Meridian - Saskatchewan, Alberta
        "W4": ["AB"],  # Fourth Meridian - Alberta
        "W5": ["AB"],  # Fifth Meridian - Alberta
        "W6": ["AB", "BC"],  # Sixth Meridian - Alberta, BC
    }

    def __init__(self, strict: bool = False):
        """
        Initialize the UWI parser.

        Args:
            strict: If True, raise exceptions on validation errors.
                   If False, return components with validation_errors populated.
        """
        self.strict = strict

    def parse(self, uwi: str) -> UWIComponents:
        """
        Parse a UWI string and return its components.

        Args:
            uwi: The UWI string to parse

        Returns:
            UWIComponents dataclass with parsed values

        Raises:
            UWIParseError: If strict mode is enabled and parsing fails
        """
        if not uwi or not isinstance(uwi, str):
            if self.strict:
                raise UWIParseError("UWI cannot be empty or non-string", str(uwi))
            return self._create_invalid_components(str(uwi), "Empty or invalid UWI")

        # Clean the UWI
        cleaned = self._clean_uwi(uwi)

        # Determine survey system and parse
        survey_system = self.get_survey_system(cleaned)

        if survey_system == UWISurveySystem.DLS:
            return self._parse_dls(cleaned, uwi)
        elif survey_system == UWISurveySystem.NTS:
            return self._parse_nts(cleaned, uwi)
        else:
            if self.strict:
                raise UWIParseError("Unable to determine survey system", uwi)
            return self._create_invalid_components(
                uwi, "Unable to determine survey system"
            )

    def _parse_dls(self, cleaned: str, raw_uwi: str) -> UWIComponents:
        """Parse a DLS format UWI."""
        # Try standard format first
        match = self.DLS_PATTERN.match(cleaned)
        if not match:
            # Try compact format
            match = self.DLS_COMPACT_PATTERN.match(cleaned)

        if not match:
            if self.strict:
                raise UWIParseError("Invalid DLS UWI format", raw_uwi)
            return self._create_invalid_components(raw_uwi, "Invalid DLS UWI format")

        groups = match.groupdict()

        components = UWIComponents(
            survey_system=UWISurveySystem.DLS,
            location_exception=groups["location_exception"],
            legal_subdivision=groups["legal_subdivision"],
            section=groups["section"],
            township=groups["township"],
            range=groups["range"],
            meridian=groups["meridian"].upper(),
            event_sequence=groups["event_sequence"],
            raw_uwi=raw_uwi,
        )

        # Set normalized UWI
        components.normalized_uwi = self.format(components)

        # Infer province from meridian
        components.province = self._infer_province_from_meridian(components.meridian)

        # Validate components
        self._validate_dls_components(components)

        return components

    def _parse_nts(self, cleaned: str, raw_uwi: str) -> UWIComponents:
        """Parse an NTS format UWI."""
        # Try full format first
        match = self.NTS_PATTERN.match(cleaned)
        if not match:
            # Try simplified format
            match = self.NTS_SIMPLE_PATTERN.match(cleaned)

        if not match:
            if self.strict:
                raise UWIParseError("Invalid NTS UWI format", raw_uwi)
            return self._create_invalid_components(raw_uwi, "Invalid NTS UWI format")

        groups = match.groupdict()

        components = UWIComponents(
            survey_system=UWISurveySystem.NTS,
            location_exception=groups["location_exception"],
            legal_subdivision=groups.get("quarter_unit", "").upper(),
            section=groups.get("unit", ""),
            township=groups.get("map_area", ""),
            range=groups.get("map_subsheet", "") or "00",
            meridian=(
                groups.get("map_sheet", "").upper() if groups.get("map_sheet") else ""
            ),
            event_sequence=groups["event_sequence"],
            raw_uwi=raw_uwi,
            # NTS-specific fields
            quarter_unit=groups.get("quarter_unit", "").upper(),
            unit=groups.get("unit", ""),
            block=groups.get("block", "").upper(),
            map_area=groups.get("map_area", ""),
            map_sheet=(
                groups.get("map_sheet", "").upper() if groups.get("map_sheet") else None
            ),
        )

        # NTS is typically BC, Yukon, or NWT
        components.province = "BC"  # Default, could be YT or NT

        # Set normalized UWI
        components.normalized_uwi = self.format(components)

        return components

    def validate(self, uwi: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a UWI format.

        Args:
            uwi: The UWI string to validate

        Returns:
            Tuple of (is_valid, error_message)
            If valid, error_message is None
        """
        if not uwi or not isinstance(uwi, str):
            return False, "UWI cannot be empty or non-string"

        cleaned = self._clean_uwi(uwi)
        survey_system = self.get_survey_system(cleaned)

        if survey_system == UWISurveySystem.UNKNOWN:
            return (
                False,
                "Unable to determine survey system (neither DLS nor NTS format)",
            )

        try:
            # Parse will validate
            components = self.parse(uwi)
            if not components.is_valid:
                errors = "; ".join(components.validation_errors)
                return False, errors
            return True, None
        except UWIParseError as e:
            return False, str(e)

    def format(self, components: UWIComponents) -> str:
        """
        Format UWI components back to a standard UWI string.

        Args:
            components: UWIComponents dataclass

        Returns:
            Formatted UWI string in standard format
        """
        if components.survey_system == UWISurveySystem.DLS:
            return (
                f"{components.location_exception}."
                f"{components.legal_subdivision}-"
                f"{components.section}-"
                f"{components.township}-"
                f"{components.range}{components.meridian}."
                f"{components.event_sequence}"
            )
        elif components.survey_system == UWISurveySystem.NTS:
            # NTS format
            parts = [
                components.location_exception,
                ".",
                components.quarter_unit or components.legal_subdivision,
                "-",
                components.unit or components.section,
                "-",
                components.block or "",
                "-",
                components.map_area or components.township,
            ]
            if components.map_sheet:
                parts.extend(["-", components.map_sheet])
            if components.range and components.range != "00":
                parts.extend(["-", components.range])
            parts.extend([".", components.event_sequence])
            return "".join(parts)
        else:
            return components.raw_uwi

    def get_survey_system(self, uwi: str) -> UWISurveySystem:
        """
        Determine the survey system (DLS or NTS) from a UWI.

        Args:
            uwi: The UWI string

        Returns:
            UWISurveySystem enum value
        """
        if not uwi:
            return UWISurveySystem.UNKNOWN

        cleaned = self._clean_uwi(uwi)

        # Check for DLS pattern (contains W followed by digit for meridian)
        if self.DLS_PATTERN.match(cleaned) or self.DLS_COMPACT_PATTERN.match(cleaned):
            return UWISurveySystem.DLS

        # Check for NTS pattern (contains letter-number-letter patterns)
        if self.NTS_PATTERN.match(cleaned) or self.NTS_SIMPLE_PATTERN.match(cleaned):
            return UWISurveySystem.NTS

        # Heuristic: DLS typically has "W" followed by a digit
        if re.search(r"W[1-6]", cleaned, re.IGNORECASE):
            return UWISurveySystem.DLS

        # Heuristic: NTS has letter-number-letter patterns
        if re.search(r"[A-D]-\d+-[A-L]", cleaned, re.IGNORECASE):
            return UWISurveySystem.NTS

        return UWISurveySystem.UNKNOWN

    def normalize(self, uwi: str) -> str:
        """
        Normalize a UWI to standard format.

        Handles various input formats and converts to the standard format:
        - DLS: LSS.LL-SS-TTT-RRWM.EE
        - NTS: LSS.Q-UUU-B-MMM-S-SS.EE

        Args:
            uwi: The UWI string to normalize

        Returns:
            Normalized UWI string
        """
        components = self.parse(uwi)
        if components.is_valid:
            return self.format(components)
        return uwi  # Return original if parsing fails

    def _clean_uwi(self, uwi: str) -> str:
        """Clean and standardize UWI string for parsing."""
        # Remove leading/trailing whitespace
        cleaned = uwi.strip()

        # Remove any spaces
        cleaned = cleaned.replace(" ", "")

        # Replace backslash with forward slash
        cleaned = cleaned.replace("\\", "/")

        # Standardize format: Convert slash-based format to period/dash format
        # Pattern: 100/16-09-010-09W4/00 should become 100.16-09-010-09W4.00
        # This handles the case where slashes are used instead of periods

        # Check if this looks like a DLS format with slashes
        dls_slash_pattern = re.match(
            r"^(\d{3})/(\d{2})-(\d{2})-(\d{3})-(\d{2})(W\d)/(\d{2})$",
            cleaned,
            re.IGNORECASE,
        )
        if dls_slash_pattern:
            groups = dls_slash_pattern.groups()
            cleaned = f"{groups[0]}.{groups[1]}-{groups[2]}-{groups[3]}-{groups[4]}{groups[5]}.{groups[6]}"

        return cleaned

    def _validate_dls_components(self, components: UWIComponents) -> None:
        """Validate DLS-specific component ranges."""
        errors = []

        # Validate legal subdivision (1-16)
        try:
            lsd = int(components.legal_subdivision)
            if not (1 <= lsd <= 16):
                errors.append(f"Legal subdivision must be 01-16, got {lsd}")
        except ValueError:
            errors.append(f"Invalid legal subdivision: {components.legal_subdivision}")

        # Validate section (1-36)
        try:
            section = int(components.section)
            if not (1 <= section <= 36):
                errors.append(f"Section must be 01-36, got {section}")
        except ValueError:
            errors.append(f"Invalid section: {components.section}")

        # Validate township (1-126)
        try:
            township = int(components.township)
            if not (1 <= township <= 126):
                errors.append(f"Township must be 001-126, got {township}")
        except ValueError:
            errors.append(f"Invalid township: {components.township}")

        # Validate range (1-34, varies by meridian)
        try:
            rng = int(components.range)
            if not (1 <= rng <= 34):
                errors.append(f"Range must be 01-34, got {rng}")
        except ValueError:
            errors.append(f"Invalid range: {components.range}")

        # Validate meridian (W1-W6)
        meridian_match = re.match(r"W(\d)", components.meridian, re.IGNORECASE)
        if meridian_match:
            m = int(meridian_match.group(1))
            if not (1 <= m <= 6):
                errors.append(f"Meridian must be W1-W6, got {components.meridian}")
        else:
            errors.append(f"Invalid meridian format: {components.meridian}")

        if errors:
            components.is_valid = False
            components.validation_errors.extend(errors)
            if self.strict:
                raise UWIParseError(
                    "DLS validation failed",
                    components.raw_uwi,
                    "; ".join(errors),
                )

    def _infer_province_from_meridian(self, meridian: str) -> Optional[str]:
        """Infer the most likely province from the meridian."""
        meridian_upper = meridian.upper()
        provinces = self.MERIDIAN_PROVINCES.get(meridian_upper, [])
        if provinces:
            # Return the most common province for this meridian
            # W4 and W5 are almost always Alberta
            if meridian_upper in ["W4", "W5"]:
                return "AB"
            elif meridian_upper == "W1":
                return "MB"
            elif meridian_upper == "W2":
                return "SK"
            elif meridian_upper == "W3":
                return "SK"  # Could also be AB
            elif meridian_upper == "W6":
                return "AB"  # Could also be BC
        return None

    def _create_invalid_components(self, raw_uwi: str, error: str) -> UWIComponents:
        """Create an invalid UWIComponents object with error information."""
        return UWIComponents(
            survey_system=UWISurveySystem.UNKNOWN,
            location_exception="",
            legal_subdivision="",
            section="",
            township="",
            range="",
            meridian="",
            event_sequence="",
            raw_uwi=raw_uwi,
            is_valid=False,
            validation_errors=[error],
        )

    def batch_parse(self, uwis: List[str]) -> List[UWIComponents]:
        """
        Parse multiple UWIs.

        Args:
            uwis: List of UWI strings

        Returns:
            List of UWIComponents, one for each input UWI
        """
        return [self.parse(uwi) for uwi in uwis]

    def batch_validate(self, uwis: List[str]) -> List[Tuple[str, bool, Optional[str]]]:
        """
        Validate multiple UWIs.

        Args:
            uwis: List of UWI strings

        Returns:
            List of tuples (uwi, is_valid, error_message)
        """
        results = []
        for uwi in uwis:
            is_valid, error = self.validate(uwi)
            results.append((uwi, is_valid, error))
        return results
