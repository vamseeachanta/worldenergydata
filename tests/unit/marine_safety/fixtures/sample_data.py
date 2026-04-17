"""Sample data generators for marine safety incident testing.

This module provides factory functions and sample data for creating
realistic test incidents, vessels, and USCG report content.
"""

import random
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from faker import Faker

fake = Faker()


# Realistic marine incident types and categories
INCIDENT_TYPES = [
    "Collision",
    "Grounding",
    "Fire/Explosion",
    "Flooding",
    "Capsizing",
    "Sinking",
    "Pollution",
    "Personal Injury",
    "Loss of Propulsion",
    "Loss of Steering",
    "Allision",  # Vessel striking fixed object
    "Damage to Equipment",
    "Man Overboard",
]

VESSEL_TYPES = [
    "Tanker",
    "Cargo Ship",
    "Passenger Vessel",
    "Fishing Vessel",
    "Towing Vessel",
    "Recreational",
    "Offshore Supply Vessel",
    "Research Vessel",
    "Military Vessel",
    "Barge",
]

WEATHER_CONDITIONS = [
    "Clear",
    "Fog",
    "Heavy Rain",
    "Snow",
    "High Winds",
    "Thunderstorms",
    "Hurricane Conditions",
    "Rough Seas",
]

CASUALTY_CAUSES = [
    "Human Error",
    "Equipment Failure",
    "Weather",
    "Navigation Error",
    "Inadequate Training",
    "Maintenance Failure",
    "Design Flaw",
    "Unknown",
]

US_PORTS = [
    "Houston, TX",
    "Los Angeles, CA",
    "New York, NY",
    "Savannah, GA",
    "Seattle, WA",
    "Miami, FL",
    "New Orleans, LA",
    "Long Beach, CA",
    "Port Everglades, FL",
    "Norfolk, VA",
    "Oakland, CA",
    "Charleston, SC",
    "Corpus Christi, TX",
    "Anchorage, AK",
    "Portland, OR",
]

WATERWAYS = [
    "Gulf of Mexico",
    "Atlantic Ocean",
    "Pacific Ocean",
    "Chesapeake Bay",
    "Puget Sound",
    "Mississippi River",
    "Delaware Bay",
    "San Francisco Bay",
    "Long Island Sound",
    "Cook Inlet",
    "Mobile Bay",
    "Tampa Bay",
]


def generate_vessel(vessel_id: Optional[str] = None) -> Dict[str, Any]:
    """Generate realistic vessel data.

    Args:
      vessel_id: Optional vessel identifier

    Returns:
      Dictionary containing vessel information
    """
    if vessel_id is None:
        vessel_id = f"IMO{fake.random_number(digits=7, fix_len=True)}"

    vessel_type = random.choice(VESSEL_TYPES)

    return {
        "vessel_id": vessel_id,
        "vessel_name": fake.company().replace(",", "").upper(),
        "vessel_type": vessel_type,
        "flag": fake.country(),
        "imo_number": f"IMO{fake.random_number(digits=7, fix_len=True)}",
        "call_sign": fake.bothify(text="???####").upper(),
        "gross_tonnage": random.randint(100, 100000),
        "year_built": random.randint(1980, 2024),
        "owner": fake.company(),
        "operator": fake.company(),
        "classification_society": random.choice(
            [
                "American Bureau of Shipping",
                "Lloyd's Register",
                "DNV GL",
                "Bureau Veritas",
                "NK Class",
            ]
        ),
    }


def generate_incident(
    incident_id: Optional[str] = None,
    date: Optional[datetime] = None,
    include_casualties: bool = None,
    include_pollution: bool = None,
) -> Dict[str, Any]:
    """Generate realistic marine incident data.

    Args:
      incident_id: Optional incident identifier
      date: Optional incident date
      include_casualties: Force inclusion of casualty data
      include_pollution: Force inclusion of pollution data

    Returns:
      Dictionary containing complete incident information
    """
    if incident_id is None:
        year = date.year if date else random.randint(2020, 2024)
        incident_id = f"USCG-{year}-{fake.random_number(digits=6, fix_len=True)}"

    if date is None:
        start_date = datetime(2020, 1, 1)
        end_date = datetime.now()
        date = fake.date_time_between(start_date=start_date, end_date=end_date)

    incident_type = random.choice(INCIDENT_TYPES)

    # Base incident data
    incident = {
        "incident_id": incident_id,
        "date": date,
        "time": date.time(),
        "location": random.choice(US_PORTS + WATERWAYS),
        "latitude": round(random.uniform(24.0, 49.0), 6),
        "longitude": round(random.uniform(-125.0, -67.0), 6),
        "incident_type": incident_type,
        "severity": random.choice(["Minor", "Moderate", "Serious", "Critical"]),
        "weather_conditions": random.choice(WEATHER_CONDITIONS),
        "sea_state": random.choice(["Calm", "Moderate", "Rough", "Very Rough"]),
        "visibility": random.choice(["Good", "Fair", "Poor", "Zero"]),
        "wind_speed_knots": random.randint(0, 50),
        "wave_height_feet": random.randint(0, 20),
        "vessel": generate_vessel(),
        "primary_cause": random.choice(CASUALTY_CAUSES),
        "investigation_status": random.choice(
            ["Open", "Under Investigation", "Closed", "Pending Review"]
        ),
        "reporting_agency": "U.S. Coast Guard",
        "narrative": fake.paragraph(nb_sentences=5),
        "recommendations": fake.paragraph(nb_sentences=3),
    }

    # Add casualties if requested or randomly
    if include_casualties or (include_casualties is None and random.random() > 0.7):
        incident.update(
            {
                "fatalities": random.randint(0, 5),
                "injuries": random.randint(0, 10),
                "casualties_description": fake.paragraph(nb_sentences=2),
            }
        )
    else:
        incident.update(
            {"fatalities": 0, "injuries": 0, "casualties_description": None}
        )

    # Add pollution data if requested or for pollution incidents
    if include_pollution or incident_type == "Pollution":
        incident.update(
            {
                "pollution_type": random.choice(
                    ["Oil", "Chemical", "Sewage", "Garbage"]
                ),
                "pollution_volume": round(random.uniform(10.0, 10000.0), 2),
                "pollution_volume_unit": random.choice(
                    ["gallons", "barrels", "liters"]
                ),
                "environmental_impact": fake.paragraph(nb_sentences=2),
            }
        )
    else:
        incident.update(
            {
                "pollution_type": None,
                "pollution_volume": None,
                "pollution_volume_unit": None,
                "environmental_impact": None,
            }
        )

    # Add damage estimate
    incident["estimated_damage_usd"] = random.randint(10000, 10000000)

    # Add vessel count for collisions
    if incident_type == "Collision":
        incident["vessels_involved"] = random.randint(2, 3)
    else:
        incident["vessels_involved"] = 1

    return incident


def generate_batch(
    count: int = 10,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Generate multiple incidents for batch testing.

    Args:
      count: Number of incidents to generate
      start_date: Start of date range
      end_date: End of date range

    Returns:
      List of incident dictionaries
    """
    if start_date is None:
        start_date = datetime(2020, 1, 1)
    if end_date is None:
        end_date = datetime.now()

    incidents = []
    for i in range(count):
        date = fake.date_time_between(start_date=start_date, end_date=end_date)
        incident = generate_incident(date=date)
        incidents.append(incident)

    return incidents


# Sample USCG report HTML
SAMPLE_USCG_REPORT = """
<!DOCTYPE html>
<html>
<head>
  <title>Marine Casualty Report - USCG-2024-001234</title>
</head>
<body>
  <div class="report-header">
    <h1>U.S. Coast Guard Marine Casualty Report</h1>
    <p>Report ID: USCG-2024-001234</p>
    <p>Date: January 15, 2024</p>
  </div>

  <div class="incident-details">
    <h2>Incident Information</h2>
    <table>
      <tr>
        <td>Incident Type:</td>
        <td>Collision</td>
      </tr>
      <tr>
        <td>Date/Time:</td>
        <td>January 15, 2024 14:30 UTC</td>
      </tr>
      <tr>
        <td>Location:</td>
        <td>Gulf of Mexico, 29.5°N 94.8°W</td>
      </tr>
      <tr>
        <td>Weather:</td>
        <td>Clear, Winds 10-15 knots</td>
      </tr>
    </table>
  </div>

  <div class="vessel-info">
    <h2>Vessel Information</h2>
    <h3>Primary Vessel</h3>
    <table>
      <tr>
        <td>Name:</td>
        <td>SEA TRADER</td>
      </tr>
      <tr>
        <td>IMO Number:</td>
        <td>IMO9123456</td>
      </tr>
      <tr>
        <td>Type:</td>
        <td>Cargo Ship</td>
      </tr>
      <tr>
        <td>Flag:</td>
        <td>United States</td>
      </tr>
      <tr>
        <td>Gross Tonnage:</td>
        <td>15,000 GT</td>
      </tr>
    </table>
  </div>

  <div class="casualties">
    <h2>Casualties</h2>
    <p>Fatalities: 0</p>
    <p>Injuries: 2 (minor)</p>
  </div>

  <div class="narrative">
    <h2>Incident Narrative</h2>
    <p>
      At approximately 1430 UTC on January 15, 2024, the motor vessel SEA TRADER
      was transiting the Gulf of Mexico when it collided with another vessel in
      restricted visibility conditions. The collision resulted in minor structural
      damage to both vessels and two crew members sustained minor injuries.
    </p>
    <p>
      The investigation determined that the primary cause was inadequate watchkeeping
      and failure to properly utilize radar equipment in reduced visibility.
    </p>
  </div>

  <div class="recommendations">
    <h2>Safety Recommendations</h2>
    <ul>
      <li>Implement enhanced bridge resource management training</li>
      <li>Review and update company SMS procedures for navigation in restricted visibility</li>
      <li>Ensure proper radar watch protocols are followed</li>
    </ul>
  </div>
</body>
</html>
"""


# Sample USCG PDF extracted text
SAMPLE_USCG_PDF_TEXT = """
U.S. COAST GUARD MARINE CASUALTY REPORT

Report Number: USCG-2024-001234
Date: January 15, 2024
Classification: Serious Marine Incident

INCIDENT DETAILS
----------------
Type: Collision
Date/Time: January 15, 2024 / 14:30 UTC
Location: Gulf of Mexico
Position: 29°30'N 094°48'W
Weather: Clear, visibility 10+ nm
Sea State: Calm to moderate, 2-3 ft waves
Wind: NE 10-15 knots

VESSEL INFORMATION
------------------
Primary Vessel:
Name: SEA TRADER
Official Number: 1234567
IMO Number: 9123456
Call Sign: WXYZ
Flag: United States
Type: Cargo Ship
Gross Tonnage: 15,000
Built: 2015
Owner: Ocean Shipping Inc.
Operator: Global Marine Transport

Secondary Vessel:
Name: PACIFIC RUNNER
IMO Number: 9234567
Type: Tanker
Flag: Panama
Gross Tonnage: 25,000

CASUALTIES AND DAMAGES
---------------------
Personnel:
- Fatalities: 0
- Injuries: 2 (minor - treated onboard)

Vessel Damage:
- SEA TRADER: Moderate damage to bow section, estimated $250,000
- PACIFIC RUNNER: Minor damage to hull plating, estimated $75,000

Pollution: None reported

INCIDENT SUMMARY
----------------
At approximately 1430 UTC, M/V SEA TRADER was proceeding on course 180° at
12 knots when it collided with M/V PACIFIC RUNNER which was on course 270°
at 10 knots. Both vessels were in international waters approximately 50
nautical miles south of Galveston, Texas.

The collision occurred in clear weather conditions with good visibility.
Radar was operational on both vessels but was not being properly monitored
on SEA TRADER.

INVESTIGATION FINDINGS
---------------------
Primary Cause: Inadequate bridge watch/lookout
Contributing Factors:
1. Failure to properly monitor radar
2. Inadequate use of sound signals
3. Non-compliance with COLREGS Rule 5 (Lookout)

The investigation determined that the watch officer on SEA TRADER was
distracted by administrative duties and failed to maintain a proper
lookout. The officer did not detect PACIFIC RUNNER on radar until less
than one minute before the collision.

PACIFIC RUNNER was maintaining a proper lookout and attempted to take
evasive action but was unable to avoid the collision due to the close
quarters situation.

SAFETY RECOMMENDATIONS
---------------------
1. Company should implement enhanced Bridge Resource Management training
   for all deck officers, emphasizing:
   - Proper radar watch procedures
   - Maintaining situational awareness
   - Task prioritization during watchkeeping

2. Review and update company Safety Management System procedures regarding:
   - Bridge watchkeeping standards
   - Use of electronic navigation equipment
   - Administrative task scheduling to avoid interference with navigation duties

3. Conduct focused training on COLREGS compliance, particularly:
   - Rule 5 (Lookout)
   - Rule 7 (Risk of Collision)
   - Rule 8 (Action to Avoid Collision)

STATUS: Investigation Closed
Date: March 30, 2024

Investigating Officer: LCDR John Smith, USCG
Report Approved By: CAPT Jane Doe, USCG
"""


# Complete sample incident with all fields
SAMPLE_INCIDENT_DATA = {
    "incident_id": "USCG-2024-001234",
    "date": datetime(2024, 1, 15, 14, 30),
    "time": datetime(2024, 1, 15, 14, 30).time(),
    "location": "Gulf of Mexico",
    "latitude": 29.5,
    "longitude": -94.8,
    "incident_type": "Collision",
    "severity": "Serious",
    "weather_conditions": "Clear",
    "sea_state": "Moderate",
    "visibility": "Good",
    "wind_speed_knots": 12,
    "wave_height_feet": 3,
    "vessel": {
        "vessel_id": "IMO9123456",
        "vessel_name": "SEA TRADER",
        "vessel_type": "Cargo Ship",
        "flag": "United States",
        "imo_number": "IMO9123456",
        "call_sign": "WXYZ",
        "gross_tonnage": 15000,
        "year_built": 2015,
        "owner": "Ocean Shipping Inc.",
        "operator": "Global Marine Transport",
        "classification_society": "American Bureau of Shipping",
    },
    "vessels_involved": 2,
    "primary_cause": "Inadequate bridge watch/lookout",
    "fatalities": 0,
    "injuries": 2,
    "casualties_description": "Two crew members sustained minor injuries, treated onboard",
    "pollution_type": None,
    "pollution_volume": None,
    "pollution_volume_unit": None,
    "environmental_impact": None,
    "estimated_damage_usd": 325000,
    "investigation_status": "Closed",
    "reporting_agency": "U.S. Coast Guard",
    "narrative": (
        "At approximately 1430 UTC, M/V SEA TRADER was proceeding on course 180° at "
        "12 knots when it collided with M/V PACIFIC RUNNER which was on course 270° "
        "at 10 knots. The collision occurred in clear weather conditions with good visibility. "
        "The watch officer on SEA TRADER was distracted by administrative duties and failed "
        "to maintain a proper lookout."
    ),
    "recommendations": (
        "Implement enhanced Bridge Resource Management training for all deck officers. "
        "Review and update company SMS procedures regarding bridge watchkeeping standards. "
        "Conduct focused training on COLREGS compliance."
    ),
}
