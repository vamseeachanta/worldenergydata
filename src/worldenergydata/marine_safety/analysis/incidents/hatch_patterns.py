# ABOUTME: Pattern definitions for hatch, door, and opening maloperation detection in marine safety.
# ABOUTME: Contains regex patterns for detection, location classification,
# consequences, and contributing factors.

"""
Hatch Maloperation Pattern Definitions

This module contains all regex pattern definitions used for detecting and classifying
hatch, door, and opening maloperation incidents. Patterns are organized by category:
- Detection patterns (hatches, doors, openings, covers, hardware)
- Location patterns (engine room, enclosures)
- Consequence patterns (flooding, fire, injury, etc.)
- Contributing factor patterns (human error, maintenance, weather, etc.)
"""

from typing import Dict, List

# Pattern matching for hatch maloperation terminology variations
# Expanded to include all door, hatch, and opening incidents
HATCH_PATTERNS: List[str] = [
    # Hatch-specific patterns
    r"\bhatch\s+maloperation\b",
    r"\bhatch\s+failure\b",
    r"\bhatch.*?failed",
    r"\bhatch.*?improperly\s+secured\b",
    r"\bhatch.*?not\s+secured\b",
    r"\bhatch.*?unsecured\b",
    r"\bhatch.*?left\s+open\b",
    r"\bhatch.*?mechanism.*?failed\b",
    r"\bhatch\s+seal\s+failure\b",
    r"\baccess\s+hatch\b",
    r"\bengine\s+room\s+hatch\b",
    r"\bcargo\s+hatch\b",
    r"\bwatertight\s+hatch\b",
    # Door-specific patterns
    r"\bdoor\s+maloperation\b",
    r"\bdoor\s+failure\b",
    r"\bdoor.*?failed",
    r"\bdoor.*?improperly\s+secured\b",
    r"\bdoor.*?not\s+secured\b",
    r"\bdoor.*?unsecured\b",
    r"\bdoor.*?left\s+open\b",
    r"\bdoor.*?mechanism.*?failed\b",
    r"\bwatertight\s+door\b",
    r"\baccess\s+door\b",
    r"\bcargo\s+door\b",
    r"\bbulkhead\s+door\b",
    r"\bfire\s+door\b",
    # General opening patterns
    r"\bopening\s+maloperation\b",
    r"\bopening\s+failure\b",
    r"\bopening.*?failed",
    r"\bopening.*?not\s+secured\b",
    r"\bopening.*?left\s+open\b",
    # Cover and seal patterns
    r"\baccess\s+cover\s+maloperation\b",
    r"\baccess\s+cover\s+failure\b",
    r"\bmanhole\s+cover\b",
    r"\bseal\s+failure\b",
    r"\bcover.*?unsecured\b",
    r"\bcover.*?not\s+secured\b",
    # Hardware failure patterns
    r"\bhinge.*?failure\b",
    r"\blatch.*?failure\b",
    r"\block.*?failure\b",
    r"\bfastener.*?failure\b",
    r"\bclosure.*?failure\b",
    # Consequence-based patterns (opening-related flooding/ingress)
    r"\bflooding.*?through.*?(?:hatch|door|opening|cover)\b",
    r"\bwater\s+ingress.*?(?:hatch|door|opening|cover)\b",
    r"\b(?:hatch|door|opening|cover).*?flooding\b",
]

# Location classification patterns
ENGINE_ROOM_PATTERNS: List[str] = [
    r"\bengine\s+room\b",
    r"\bmachinery\s+space\b",
    r"\bmain\s+engine\b",
    r"\bengine\s+compartment\b",
]

ENCLOSURE_PATTERNS: List[str] = [
    r"\benclosure\b",
    r"\bcompartment\b",
    r"\bdeck\s+access\b",
    r"\bstorage\s+space\b",
    r"\bcargo\s+hold\b",
    r"\btank\s+access\b",
]

# Consequence patterns
CONSEQUENCE_PATTERNS: Dict[str, List[str]] = {
    "flooding": [
        r"\bflood(?:ing|ed)\b",
        r"\bwater\s+ingress\b",
        r"\btook\s+on\s+water\b",
        r"\bbilge\s+pumps?\b",
    ],
    "fire": [
        r"\bfire\b",
        r"\bignition\b",
        r"\bburns?\b",
        r"\bflames?\b",
        r"\bfire\s+suppression\b",
    ],
    "personnel_injury": [
        r"\binjur(?:y|ies|ed)\b",
        r"\bhurt\b",
        r"\bfracture\b",
        r"\bwound(?:ed|s)?\b",
    ],
    "fatality": [
        r"\bfatalit(?:y|ies)\b",
        r"\bdeath(?:s)?\b",
        r"\blost\b.*\bcrew\b",
        r"\bkilled\b",
    ],
    "equipment_damage": [
        r"\bequipment\s+damage\b",
        r"\bdamaged?\b",
        r"\bfailure\b",
    ],
    "vessel_stability": [
        r"\blist(?:ed|ing)\b",
        r"\bstability\b",
        r"\bcapsize\b",
        r"\bheeling\b",
    ],
    "near_miss": [
        r"\bnear\s+miss\b",
        r"\bpreventive\b",
        r"\bdetected\s+during\s+inspection\b",
        r"\bcould\s+have\b",
    ],
}

# Contributing factor patterns
FACTOR_PATTERNS: Dict[str, List[str]] = {
    "human_error": [
        r"\bcrew.*?failed\b",
        r"\bfailed\s+to\s+secure\b",
        r"\bfailed\s+to\s+properly\b",
        r"\bimproperly\b",
        r"\bnegligence\b",
        r"\binadequate\s+training\b",
    ],
    "maintenance_issue": [
        r"\bmaintenance\b",
        r"\bimproperly\s+maintained\b",
        r"\black\s+of\s+maintenance\b",
        r"\bpreventive\s+maintenance\b",
        r"\bwear\s+and\s+tear\b",
    ],
    "equipment_failure": [
        r"\bequipment\s+failure\b",
        r"\bmechanism.*?failed\b",
        r"\bseal\s+failure\b",
        r"\bdefective\b",
        r"\bmalfunctioned\b",
    ],
    "weather": [
        r"\bheavy\s+seas?\b",
        r"\bstorm\b",
        r"\brough\s+(?:seas?|weather)\b",
        r"\bhigh\s+winds?\b",
        r"\badverse\s+(?:weather|conditions)\b",
    ],
    "design_flaw": [
        r"\bdesign\s+flaw\b",
        r"\binadequate\s+design\b",
        r"\bstructural\s+weakness\b",
    ],
}

# Severity score mapping
SEVERITY_SCORES: Dict[str, int] = {
    "Minor": 10,
    "Moderate": 15,
    "Serious": 20,
    "Critical": 25,
    "Catastrophic": 30,
}

# High-impact consequences for risk scoring
HIGH_IMPACT_CONSEQUENCES: List[str] = [
    "flooding",
    "fire",
    "fatality",
    "vessel_stability",
]
