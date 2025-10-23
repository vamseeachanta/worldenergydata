# Incident Cause Mapping Reference

**Version:** 1.0
**Last Updated:** 2025-10-22
**Purpose:** Quick reference for mapping raw data fields to standardized cause categories

---

## Quick Reference Tables

### TSB AccIncTypeDisplayEng → CauseCategory

```python
TSB_CAUSE_MAPPING = {
    # Equipment and mechanical failures
    "TOTAL FAILURE OF ANY MACHINERY OR TECHNICAL SYSTEM": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"],
        "confidence": 0.9
    },
    "RISK OF SINKING": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE", "WEATHER"],
        "confidence": 0.7
    },

    # Navigation errors
    "GROUNDING - Under power (non-intentional)": {
        "primary": "HUMAN_ERROR",
        "secondary": ["EQUIPMENT_FAILURE"],
        "confidence": 0.9
    },
    "GROUNDING - Not under power (includes drifting) (non-intentional)": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["WEATHER"],
        "confidence": 0.8
    },
    "STRIKING - Allision with a fixed object (striking - includes berthed/docked vessels)": {
        "primary": "HUMAN_ERROR",
        "secondary": ["EQUIPMENT_FAILURE"],
        "confidence": 0.85
    },
    "BOTTOM CONTACT": {
        "primary": "HUMAN_ERROR",
        "secondary": ["EQUIPMENT_FAILURE"],
        "confidence": 0.8
    },

    # Collisions
    "COLLISION - With another vessel or other floating object": {
        "primary": "HUMAN_ERROR",
        "secondary": ["COMMUNICATION", "WEATHER"],
        "confidence": 0.9
    },
    "COLLISION - Struck by vessel": {
        "primary": "HUMAN_ERROR",
        "secondary": ["COMMUNICATION"],
        "confidence": 0.85
    },
    "RISK OF COLLISION (near collision) - With another vessel or other floating object": {
        "primary": "HUMAN_ERROR",
        "secondary": ["COMMUNICATION"],
        "confidence": 0.8
    },
    "RISK OF STRIKING (near allision) - Risk of allision with a fixed object (striking - includes vessels)": {
        "primary": "HUMAN_ERROR",
        "secondary": ["EQUIPMENT_FAILURE"],
        "confidence": 0.8
    },

    # Fire and explosion
    "FIRE": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE", "PROCEDURAL"],
        "confidence": 0.8
    },
    "EXPLOSION": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["PROCEDURAL", "MAINTENANCE_ISSUE"],
        "confidence": 0.85
    },

    # Flooding and sinking
    "SANK - Flooding": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["WEATHER", "MAINTENANCE_ISSUE"],
        "confidence": 0.8
    },
    "SANK - Founders (taking on water above the waterline)": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["DESIGN_FLAW", "WEATHER"],
        "confidence": 0.75
    },

    # Stability issues
    "CAPSIZES": {
        "primary": "DESIGN_FLAW",
        "secondary": ["WEATHER", "PROCEDURAL"],
        "confidence": 0.8
    },

    # Personnel safety
    "PERSON SERIOUSLY INJURED OR KILLED - In contact with any part of the ship or its contents": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL", "TRAINING"],
        "confidence": 0.85
    },
    "PERSON SERIOUSLY INJURED OR KILLED - Boarding, being on board, falling overboard from the ship": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL", "WEATHER"],
        "confidence": 0.85
    },
    "PERSON OVERBOARD": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL", "WEATHER"],
        "confidence": 0.85
    },

    # Weather and environmental
    "SUSTAINS DAMAGE RENDER UNSEAWORTHY/UNFIT FOR PURPOSE - Unfit for purpose - ice, weather, etc.": {
        "primary": "WEATHER",
        "secondary": ["DESIGN_FLAW", "MAINTENANCE_ISSUE"],
        "confidence": 0.9
    },

    # Cargo operations
    "CARGO SHIFT/CARGO LOSS - Cargo shifted": {
        "primary": "PROCEDURAL",
        "secondary": ["WEATHER", "HUMAN_ERROR"],
        "confidence": 0.85
    },
    "CARGO SHIFT/CARGO LOSS - Cargo lost overboard": {
        "primary": "PROCEDURAL",
        "secondary": ["WEATHER", "EQUIPMENT_FAILURE"],
        "confidence": 0.8
    },

    # Intentional actions
    "INTENTIONAL BEACHING/GROUNDING/ANCHORING to avoid occurrence": {
        "primary": "PROCEDURAL",
        "secondary": ["EQUIPMENT_FAILURE", "WEATHER"],
        "confidence": 0.95
    }
}
```

### IMO GISIS Casualty Event → CauseCategory

```python
IMO_CAUSE_MAPPING = {
    # Collisions
    "Collision - with other ship": {
        "primary": "HUMAN_ERROR",
        "secondary": ["COMMUNICATION"],
        "confidence": 0.9
    },
    "Collision - own ship not under way": {
        "primary": "EXTERNAL",
        "secondary": ["HUMAN_ERROR"],
        "confidence": 0.8
    },
    "Collision - with multiple ships": {
        "primary": "HUMAN_ERROR",
        "secondary": ["COMMUNICATION", "WEATHER"],
        "confidence": 0.85
    },

    # Fire and explosion
    "Fire/explosion - fire": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"],
        "confidence": 0.85
    },
    "Fire/explosion - explosion": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["PROCEDURAL"],
        "confidence": 0.85
    },

    # Grounding
    "Grounding - while under power": {
        "primary": "HUMAN_ERROR",
        "secondary": ["EQUIPMENT_FAILURE"],
        "confidence": 0.9
    },
    "Grounding - while drifting": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["WEATHER"],
        "confidence": 0.85
    },

    # Occupational accidents (all map to HUMAN_ERROR + PROCEDURAL)
    "Occupational accident - slipping, stumbling, falling of person\r\noverboard": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL", "WEATHER"],
        "confidence": 0.85
    },
    "Occupational accident - slipping, stumbling, falling of person to a\r\nlower level": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL"],
        "confidence": 0.85
    },
    "Occupational accident - Others": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL"],
        "confidence": 0.7
    },
    "Occupational accident - body movement without any physical\r\nstress (generally leading to an external\r\ninjury)": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL", "TRAINING"],
        "confidence": 0.8
    },
    "Occupational accident - loss of control of machine, means of\r\ntransport or handling equipment,\r\nhand-held tool, object, animal": {
        "primary": "HUMAN_ERROR",
        "secondary": ["EQUIPMENT_FAILURE", "TRAINING"],
        "confidence": 0.8
    },
    "Occupational accident - breakage, bursting, splitting, fall or\r\ncollapse of material agent": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"],
        "confidence": 0.8
    },
    "Occupational accident - overflow, overturn, leak, flow,\r\nvaporization, emission of material agent": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["PROCEDURAL"],
        "confidence": 0.8
    },
    "Occupational accident - body movement under or with physical\r\nstress (generally leading to an internal\r\ninjury)\r": {
        "primary": "HUMAN_ERROR",
        "secondary": ["TRAINING"],
        "confidence": 0.85
    },
    "Occupational accident - electrical problems, explosion, fire": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"],
        "confidence": 0.9
    },
    "Occupational accident - Slipping, stumbling, falling of a person on\r\nthe same level\r": {
        "primary": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL"],
        "confidence": 0.85
    },
    "Occupational accident - shock, fright, violence, aggression,\r\nthreat, presence": {
        "primary": "EXTERNAL",
        "secondary": ["MANAGEMENT"],
        "confidence": 0.7
    },

    # Flooding and foundering
    "Flooding/foundering - flooding": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["WEATHER"],
        "confidence": 0.8
    },
    "Flooding/foundering - foundering": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["DESIGN_FLAW", "WEATHER"],
        "confidence": 0.75
    },

    # Contact
    "Contact - with fixed object": {
        "primary": "HUMAN_ERROR",
        "secondary": ["EQUIPMENT_FAILURE"],
        "confidence": 0.85
    },
    "Contact - with floating object": {
        "primary": "EXTERNAL",
        "secondary": ["WEATHER"],
        "confidence": 0.8
    },

    # Loss of control
    "Loss of control - loss of propulsion power": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"],
        "confidence": 0.9
    },
    "Loss of control - loss of directional control": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"],
        "confidence": 0.9
    },
    "Loss of control - loss of electrical power": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"],
        "confidence": 0.9
    },
    "Loss of control - loss of containment": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE", "PROCEDURAL"],
        "confidence": 0.85
    },

    # Stability
    "Capsize/listing - capsize": {
        "primary": "DESIGN_FLAW",
        "secondary": ["WEATHER", "PROCEDURAL"],
        "confidence": 0.8
    },
    "Capsize/listing - listing": {
        "primary": "PROCEDURAL",
        "secondary": ["DESIGN_FLAW", "EQUIPMENT_FAILURE"],
        "confidence": 0.75
    },

    # Structural
    "Hull failure - hull failure": {
        "primary": "DESIGN_FLAW",
        "secondary": ["MAINTENANCE_ISSUE", "WEATHER"],
        "confidence": 0.8
    },
    "Ship/equipment damage - ship/equipment damage": {
        "primary": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE", "EXTERNAL"],
        "confidence": 0.7
    },

    # Unknown
    "Unknown - Unknown": {
        "primary": "UNKNOWN",
        "secondary": [],
        "confidence": 0.5
    },
    "Ship missing - ship missing": {
        "primary": "UNKNOWN",
        "secondary": ["WEATHER"],
        "confidence": 0.3
    },
    "Others - Others": {
        "primary": "UNKNOWN",
        "secondary": [],
        "confidence": 0.4
    }
}
```

---

## Keyword-Based Cause Detection

### Equipment-Specific Keywords

```python
EQUIPMENT_KEYWORDS = {
    "hatch": ["hatch", "hatch cover", "cargo hatch", "hatchway", "weathertight hatch", "watertight hatch"],
    "engine": ["engine", "motor", "propulsion", "diesel", "turbine", "generator"],
    "steering": ["steering", "rudder", "helm", "autopilot", "steering gear"],
    "navigation": ["radar", "gps", "compass", "chart plotter", "ais", "navigation"],
    "communication": ["radio", "vhf", "satellite", "communication", "epirb"],
    "electrical": ["electrical", "power", "battery", "circuit", "wiring", "generator"],
    "hydraulic": ["hydraulic", "pump", "pressure", "fluid", "cylinder"],
    "anchor": ["anchor", "windlass", "chain", "anchoring"],
    "bilge": ["bilge", "bilge pump", "dewatering", "water removal"],
    "hull": ["hull", "breach", "crack", "hole", "damage to hull"],
    "deck": ["deck", "deck equipment", "winch", "crane", "davit"],
    "cargo": ["cargo", "loading", "unloading", "stowage", "lashing"]
}

HUMAN_ERROR_KEYWORDS = {
    "procedural": ["procedure", "did not follow", "failed to", "improper", "incorrect"],
    "navigation": ["navigation error", "wrong course", "chart error", "position error"],
    "watch": ["watch", "lookout", "fatigue", "fell asleep", "inattention"],
    "operation": ["misoperation", "incorrect operation", "improper use", "operated incorrectly"],
    "training": ["untrained", "lack of training", "inexperienced", "unfamiliar"],
    "communication": ["miscommunication", "failed to communicate", "no communication", "language barrier"],
    "judgment": ["poor judgment", "misjudged", "error in judgment", "decision error"]
}

MAINTENANCE_KEYWORDS = {
    "deferred": ["deferred maintenance", "overdue maintenance", "delayed repair"],
    "corrosion": ["corrosion", "rust", "deterioration", "decay"],
    "wear": ["wear", "worn", "fatigue", "erosion"],
    "inspection": ["failed inspection", "no inspection", "overdue inspection"],
    "repair": ["inadequate repair", "improper repair", "failed repair"]
}

WEATHER_KEYWORDS = {
    "wind": ["high wind", "strong wind", "gale", "storm", "hurricane"],
    "sea": ["heavy seas", "rough seas", "high waves", "sea state"],
    "visibility": ["fog", "reduced visibility", "low visibility", "poor visibility"],
    "ice": ["ice", "icing", "frozen", "pack ice", "iceberg"],
    "current": ["current", "tidal current", "strong current"]
}
```

### Hatch-Specific Cause Keywords

```python
HATCH_CAUSE_KEYWORDS = {
    "unsecured": {
        "keywords": ["not secured", "not closed", "open", "unsecured", "not latched", "unlocked"],
        "cause": "PROCEDURAL",
        "secondary": ["HUMAN_ERROR"]
    },
    "malfunction": {
        "keywords": ["malfunction", "maloperation", "failed to operate", "jammed", "stuck"],
        "cause": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE"]
    },
    "structural": {
        "keywords": ["cracked", "broken", "damaged", "deformed", "bent", "ruptured"],
        "cause": "EQUIPMENT_FAILURE",
        "secondary": ["MAINTENANCE_ISSUE", "EXTERNAL"]
    },
    "corrosion": {
        "keywords": ["corroded", "rusted", "deteriorated", "weakened", "thinned"],
        "cause": "MAINTENANCE_ISSUE",
        "secondary": ["DESIGN_FLAW"]
    },
    "impact": {
        "keywords": ["struck", "impact", "hit", "collision with", "crane damage", "loader damage"],
        "cause": "EXTERNAL",
        "secondary": ["PROCEDURAL"]
    },
    "water_ingress": {
        "keywords": ["water through hatch", "flooding through", "ingress", "leak"],
        "cause": "EQUIPMENT_FAILURE",
        "secondary": ["PROCEDURAL", "WEATHER"]
    },
    "personnel": {
        "keywords": ["fell through", "fell into", "through hatch", "open hatch injury"],
        "cause": "HUMAN_ERROR",
        "secondary": ["PROCEDURAL"]
    }
}
```

---

## Confidence Scoring Guidelines

### Confidence Levels

```python
CONFIDENCE_LEVELS = {
    0.9-1.0: "High - Direct keyword match or clear incident type mapping",
    0.7-0.89: "Medium-High - Strong indicators but some ambiguity",
    0.5-0.69: "Medium - Multiple possible causes or limited information",
    0.3-0.49: "Low - Significant uncertainty or conflicting indicators",
    0.0-0.29: "Very Low - Minimal information or unknown incident type"
}
```

### Confidence Calculation

```python
def calculate_cause_confidence(incident_type, summary_text, cause_keywords):
    """
    Calculate confidence score for cause classification

    Factors:
    - Incident type mapping confidence (base)
    - Keyword match strength (+/- 0.1)
    - Multiple keyword matches (+0.05 per additional)
    - Conflicting indicators (-0.2)
    """
    base_confidence = TSB_CAUSE_MAPPING[incident_type]["confidence"]

    # Keyword matching
    keyword_matches = count_keyword_matches(summary_text, cause_keywords)
    keyword_bonus = min(0.15, keyword_matches * 0.05)

    # Check for conflicts
    conflict_penalty = check_conflicting_causes(summary_text)

    final_confidence = max(0.0, min(1.0,
        base_confidence + keyword_bonus - conflict_penalty
    ))

    return final_confidence
```

---

## Implementation Examples

### Example 1: Simple Mapping

```python
from worldenergydata.modules.marine_safety.constants import CauseCategory

def map_tsb_cause(incident_type: str) -> dict:
    """Map TSB incident type to cause category"""
    mapping = TSB_CAUSE_MAPPING.get(incident_type)

    if not mapping:
        return {
            "primary": CauseCategory.UNKNOWN,
            "secondary": [],
            "confidence": 0.0
        }

    return {
        "primary": CauseCategory[mapping["primary"]],
        "secondary": [CauseCategory[c] for c in mapping["secondary"]],
        "confidence": mapping["confidence"]
    }

# Usage
incident_type = "GROUNDING - Under power (non-intentional)"
causes = map_tsb_cause(incident_type)
print(f"Primary: {causes['primary']}")
print(f"Secondary: {causes['secondary']}")
print(f"Confidence: {causes['confidence']}")
```

### Example 2: Enhanced Keyword-Based Extraction

```python
import re
from typing import List, Tuple

def extract_hatch_causes(summary: str) -> List[Tuple[str, float]]:
    """Extract hatch-specific causes from incident summary"""
    causes = []
    summary_lower = summary.lower()

    for cause_type, config in HATCH_CAUSE_KEYWORDS.items():
        for keyword in config["keywords"]:
            if keyword in summary_lower:
                causes.append((
                    config["cause"],
                    config["secondary"],
                    0.8  # Base confidence for keyword match
                ))
                break  # Only count once per cause type

    return causes

# Usage
summary = "Crew member fell through open hatch that was not secured"
causes = extract_hatch_causes(summary)
for primary, secondary, conf in causes:
    print(f"Cause: {primary}, Contributing: {secondary}, Confidence: {conf}")
```

### Example 3: Multi-Cause Detection

```python
def detect_multiple_causes(incident_type: str, summary: str) -> dict:
    """Detect all potential causes with confidence scores"""

    # Start with incident type mapping
    type_causes = map_tsb_cause(incident_type)

    # Extract keyword-based causes
    keyword_causes = extract_all_causes(summary)

    # Merge and rank
    all_causes = merge_causes(type_causes, keyword_causes)

    # Sort by confidence
    ranked_causes = sorted(
        all_causes.items(),
        key=lambda x: x[1]["confidence"],
        reverse=True
    )

    return {
        "primary": ranked_causes[0] if ranked_causes else None,
        "contributing": ranked_causes[1:],
        "total_confidence": calculate_overall_confidence(ranked_causes)
    }
```

---

## Data Validation Rules

### Mandatory Checks

```python
VALIDATION_RULES = {
    "incident_id": "required",
    "incident_type": "required",
    "cause_category": "must be valid CauseCategory enum",
    "is_primary": "required boolean",
    "confidence": "must be between 0.0 and 1.0",
    "cause_description": "optional but recommended",
    "contributing_factor": "optional"
}

def validate_cause_mapping(cause_data: dict) -> List[str]:
    """Validate cause mapping data"""
    errors = []

    # Required fields
    if not cause_data.get("cause_category"):
        errors.append("cause_category is required")

    # Valid enum
    try:
        CauseCategory[cause_data["cause_category"]]
    except KeyError:
        errors.append(f"Invalid cause_category: {cause_data['cause_category']}")

    # Confidence range
    confidence = cause_data.get("confidence", 0.0)
    if not 0.0 <= confidence <= 1.0:
        errors.append(f"confidence must be 0.0-1.0, got {confidence}")

    return errors
```

---

## Usage Guidelines

### When to Use Each Mapping

1. **TSB_CAUSE_MAPPING**: Use for all Canadian TSB incident data
   - High confidence for structured incident types
   - Supplement with keyword analysis for detailed classification

2. **IMO_CAUSE_MAPPING**: Use for IMO GISIS data
   - International standardization
   - May need adjustment for specific jurisdictions

3. **Keyword-Based Detection**: Use when:
   - Incident type is ambiguous or "Other"
   - Multiple causes suspected
   - High-detail classification needed
   - Validating incident type classifications

### Quality Assurance

**Manual Review Required When:**
- Confidence < 0.7
- Conflicting causes detected
- "Unknown" or "Other" incident types
- High-severity incidents (fatalities, major casualties)
- Unusual or complex incidents

**Automated Processing Acceptable When:**
- Confidence > 0.85
- Clear incident type mapping
- Single primary cause identified
- Low to moderate severity

---

## Update History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-10-22 | Initial release with TSB and IMO mappings |

---

## Related Documentation

- [Incident Cause Research](./incident_cause_research.md) - Full analysis and findings
- [Database Models](../../src/worldenergydata/modules/marine_safety/database/models.py)
- [Constants](../../src/worldenergydata/modules/marine_safety/constants.py)
