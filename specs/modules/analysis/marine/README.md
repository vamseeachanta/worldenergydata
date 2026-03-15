# Marine Safety Incident Analysis Module - Planning Documentation

## Overview

This directory contains comprehensive planning documentation for the **Marine Safety Incident Analysis & Exploration Module** - a general-purpose framework for analyzing ANY category of marine incidents and identifying their root causes.

---

## 📁 Documentation Structure

### Core Specifications

1. **[FOUNDERING_INCIDENT_ANALYSIS_SPEC.md](./FOUNDERING_INCIDENT_ANALYSIS_SPEC.md)** *(In Progress)*
   - Main module specification (being updated for general-purpose analysis)
   - Functional requirements
   - Technical architecture
   - Configuration examples
   - Expected outputs

2. **[INCIDENT_TAXONOMY.md](./INCIDENT_TAXONOMY.md)** ✅
   - Complete incident categorization system
   - Root cause categories and classifications
   - Data source field mappings
   - Search & filter examples

3. **[IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)** ✅
   - 5-week implementation plan
   - Phase-by-phase deliverables
   - Code structure and examples
   - Testing strategy

### Supporting Documentation

4. **[MARINE_SAFETY_SPEC.md](./MARINE_SAFETY_SPEC.md)** (Existing)
   - Overall marine safety module architecture
   - Database schema
   - Data sources and importers

5. **Infrastructure/** (Existing)
   - Docker compose configurations
   - Deployment guides

---

## 🎯 Module Capabilities

This module enables comprehensive analysis of **ALL** incident types:

### Incident Categories Supported

✅ **Collisions & Contact**
- Vessel-to-vessel collisions
- Fixed object strikes
- Allisions
- Submerged object strikes

✅ **Grounding & Stranding**
- Powered groundings
- Drift groundings
- Stranding incidents

✅ **Flooding & Foundering**
- Progressive/sudden flooding
- Foundering (sinking)
- Capsizing
- Listing

✅ **Fire & Explosion**
- Engine room fires
- Accommodation fires
- Cargo fires
- Fuel/cargo explosions

✅ **Machinery & Equipment Failure**
- Propulsion failures
- Steering failures
- Equipment malfunctions
- Structural failures

✅ **Human Casualties**
- Falls overboard
- Occupational accidents
- Serious injuries/fatalities

✅ **Environmental & Weather**
- Storm damage
- Heavy weather incidents
- Ice damage

✅ **Hazardous Materials**
- Pollution events
- Chemical spills
- Hazmat incidents

### Root Cause Analysis

The module identifies:
- **Human Factors**: Operator error, fatigue, procedural violations
- **Equipment Failures**: Machinery, structural, safety equipment
- **Environmental Factors**: Weather, sea state, visibility
- **Maintenance Issues**: Poor maintenance, age-related deterioration
- **Operational Factors**: Loading issues, inadequate procedures

---

## 🚀 Quick Start

### Example Use Cases

#### 1. Foundering Incidents with Hatch/Door Issues

```yaml
# config/analysis/foundering_hatch_door.yml
data_sources:
  enabled: [imo_gisis, uk_maib, canadian_tsb, us_dlp_historical]
  date_range:
    start: 1990-01-01
    end: 2025-12-31

filters:
  incident_types: [Foundering, Flooding, Sinking]
  cause_keywords: [hatch, door, watertight, hatch cover, unsealed]
  severity: [Very Serious Marine Casualty, Marine Casualty]

analysis:
  temporal: true
  vessel: true
  geographic: true
  causal: true

output:
  format: html
  filename: foundering_hatch_door_analysis.html
```

#### 2. Collision Analysis - Visibility & Fatigue

```yaml
# config/analysis/collision_visibility_fatigue.yml
filters:
  incident_types: [Collision]
  contributing_factors: [Fog, Poor Visibility, Darkness, Operator Fatigue]
  human_factors: [No Proper Lookout, Operator Inattention]

analysis:
  comparative: true
  compare_dimensions: [time_of_day, weather_condition, watch_period]
```

#### 3. Machinery Failure Trends by Vessel Type

```yaml
# config/analysis/machinery_failure_trends.yml
filters:
  incident_types: [Machinery Failure, Loss of Propulsion, Engine Failure]
  vessel_types: [General Cargo, Bulk Carrier, Tanker, Container]
  vessel_age_min: 10

analysis:
  temporal: true
  vessel: true
  comparative: true
  pattern_detection: true
```

#### 4. Geographic Hotspot Analysis

```yaml
# config/analysis/geographic_hotspots.yml
filters:
  severity: [Very Serious Marine Casualty]
  location_type: [Narrow Channel, Congested Waters]

analysis:
  geographic: true
  hotspot_detection: true
  density_analysis: true

visualization:
  map_type: interactive
  clustering: true
```

---

## 📊 Data Sources

The module integrates data from:

| Source | Coverage | Records | Key Fields |
|--------|----------|---------|-----------|
| **IMO GISIS** | 1900-2025 | 1,525+ | Casualty event, severity, vessel details |
| **UK MAIB** | 2021-2024 | 5,878+ | Multi-level events, detailed descriptions |
| **Canadian TSB** | Historical | 86,290+ | Comprehensive incident classification |
| **US DLP** | 1995-2012 | 93,238+ | Detailed causes and narratives |
| **BSEE Offshore** | 2007-2023 | Varies | Offshore platform incidents |

**Total Records**: 180,000+ marine incidents

---

## 🏗️ Module Architecture

```
src/worldenergydata/modules/marine_safety/analysis/
│
├── incidents/                    # Core incident analysis
│   ├── explorer.py              # Multi-source data loader
│   ├── categorizer.py           # Incident classification
│   ├── cause_analyzer.py        # Root cause detection
│   ├── pattern_detector.py      # Pattern & trend analysis
│   └── comparative_analyzer.py  # Comparative analysis
│
├── filters/                      # Filtering & search
│   ├── incident_filters.py      # Multi-criteria filters
│   ├── text_analyzers.py        # Text pattern matching
│   └── query_builder.py         # Dynamic queries
│
├── visualizations/               # Plotly charts
│   ├── incident_charts.py       # General visualizations
│   ├── causal_analysis.py       # Cause-effect charts
│   ├── comparative_charts.py    # Comparison plots
│   └── geospatial.py           # Maps & hotspots
│
└── reports/                      # Report generation
    ├── report_generator.py      # HTML report builder
    ├── templates/               # Report templates
    └── exporters.py            # CSV/JSON export
```

---

## 🧪 Testing Approach (TDD)

All development follows Test-Driven Development:

1. **Write failing test** → Define expected behavior
2. **Implement minimal code** → Make test pass
3. **Refactor** → Improve code quality
4. **Repeat** → For each feature

**Test Coverage Target**: >85%

---

## 📈 Expected Outputs

### Interactive HTML Reports

**Executive Summary**
- KPI dashboard (incidents, fatalities, vessel losses)
- Key findings and trends
- Filter summary

**Analysis Sections**
- Temporal analysis (trends, seasonal patterns)
- Vessel analysis (by type, age, flag)
- Geographic analysis (maps, hotspots)
- Causal analysis (root causes, factors)
- Comparative analysis (when applicable)

**All charts are interactive** (Plotly):
- Zoom, pan, export
- Hover for details
- Toggle data series
- Responsive design

### CSV Exports

- `incidents_filtered.csv` - Filtered incident dataset
- `temporal_analysis.csv` - Time-based statistics
- `vessel_analysis.csv` - Vessel-focused statistics
- `geographic_analysis.csv` - Location-based data
- `causal_analysis.csv` - Root cause breakdown
- `summary_statistics.csv` - Overall metrics

### JSON Summaries

- Machine-readable analysis results
- API-compatible format
- Metadata and configurations

---

## 🔧 Configuration System

### Configuration File Structure

```yaml
meta:
  library: worldenergydata
  module: marine_safety
  analysis_type: custom_incident_analysis
  label: my_analysis_v1

data_sources:
  enabled: [imo_gisis, uk_maib, canadian_tsb, us_dlp_historical]
  date_range:
    start: 2000-01-01
    end: 2024-12-31

filters:
  # Incident type filters
  incident_types: []              # Primary classification
  sub_types: []                   # Secondary classification
  severity_levels: []             # Casualty severity

  # Temporal filters
  seasons: []                     # [Winter, Spring, Summer, Fall]
  time_of_day: []                 # [Day, Night, Twilight]

  # Vessel filters
  vessel_types: []                # [Cargo, Tanker, Passenger, etc.]
  flag_states: []                 # Country codes
  vessel_age_range: [min, max]
  tonnage_range: [min, max]

  # Geographic filters
  regions: []                     # Geographic regions
  location_types: []              # [Port, Open Sea, Coastal, etc.]

  # Causal filters
  root_causes: []                 # Primary causes
  contributing_factors: []        # Secondary factors
  human_factors: []               # Human-related causes
  equipment_failures: []          # Equipment issues

  # Text search
  keywords: []                    # Search keywords
  exclude_keywords: []            # Exclusion patterns
  min_confidence: 0.7             # Classification confidence

analysis:
  temporal: true                  # Enable temporal analysis
  vessel: true                    # Enable vessel analysis
  geographic: true                # Enable geographic analysis
  causal: true                    # Enable causal analysis
  comparative: false              # Enable comparative analysis
  pattern_detection: false        # Enable pattern detection

reporting:
  format: html                    # Output format
  interactive: true               # Interactive charts
  visualization_library: plotly   # Chart library

  sections:                       # Report sections to include
    - executive_summary
    - temporal_analysis
    - vessel_analysis
    - geographic_analysis
    - causal_analysis

  export:
    csv: true                     # Export CSV files
    json: true                    # Export JSON summary

output:
  directory: reports/marine_safety/
  filename_pattern: "{analysis_type}_{date}.html"
  csv_directory: data/results/
```

---

## 📋 Implementation Status

### ✅ Completed
- [x] Module planning and specification
- [x] Incident taxonomy definition
- [x] Implementation roadmap
- [x] Configuration system design

### 🚧 In Progress
- [ ] Core module specification (updating for general-purpose)

### 📅 Planned (5-week timeline)
- **Week 1**: Data pipeline & unified model
- **Week 2**: Categorization & filtering system
- **Week 3**: Analysis engines
- **Week 4**: Visualization & reporting
- **Week 5**: CLI, documentation & testing

---

## 💡 Example Analysis Scenarios

### Scenario 1: Safety Trend Analysis
**Question**: "How have foundering incidents changed over the past 20 years?"

**Configuration**:
```yaml
filters:
  incident_types: [Foundering]
  date_range: [2000-01-01, 2024-12-31]
analysis:
  temporal: true
  pattern_detection: true
```

**Output**: Trend charts, seasonal patterns, regulatory impact analysis

---

### Scenario 2: Fleet Risk Assessment
**Question**: "Which vessel types have the highest collision rates?"

**Configuration**:
```yaml
filters:
  incident_types: [Collision]
  vessel_types: [General Cargo, Bulk Carrier, Tanker, Container, Passenger]
analysis:
  vessel: true
  comparative: true
```

**Output**: Risk profiles by vessel type, age correlation, flag state comparison

---

### Scenario 3: Root Cause Investigation
**Question**: "What are the primary causes of machinery failures leading to groundings?"

**Configuration**:
```yaml
filters:
  incident_types: [Grounding]
  root_causes: [Machinery Failure, Loss of Propulsion]
analysis:
  causal: true
  pattern_detection: true
```

**Output**: Cause breakdown, failure mode analysis, maintenance correlation

---

### Scenario 4: Geographic Safety Assessment
**Question**: "Identify high-risk areas for specific incident types"

**Configuration**:
```yaml
filters:
  severity: [Very Serious Marine Casualty]
analysis:
  geographic: true
  hotspot_detection: true
```

**Output**: Interactive maps, density heatmaps, regional statistics

---

## 🔗 Related Documentation

- **Main Spec**: [FOUNDERING_INCIDENT_ANALYSIS_SPEC.md](./FOUNDERING_INCIDENT_ANALYSIS_SPEC.md)
- **Taxonomy**: [INCIDENT_TAXONOMY.md](./INCIDENT_TAXONOMY.md)
- **Roadmap**: [IMPLEMENTATION_ROADMAP.md](./IMPLEMENTATION_ROADMAP.md)
- **Marine Safety Module**: [MARINE_SAFETY_SPEC.md](./MARINE_SAFETY_SPEC.md)

---

## 🤝 Contributing

When implementing this module:

1. **Follow TDD**: Write tests first
2. **Code Standards**: Adhere to project coding guidelines (see `/CLAUDE.md`)
3. **Documentation**: Update docs as you implement
4. **Test Coverage**: Maintain >85% coverage
5. **HTML Reports**: Use Plotly for all visualizations (project requirement)
6. **File Organization**: Never save to root folder - use appropriate subdirectories

---

## 📞 Support & Questions

For questions about this specification:
1. Review all three core documents
2. Check the incident taxonomy for categorization questions
3. Refer to the implementation roadmap for technical details
4. Consult existing marine_safety module code for patterns

---

**Documentation Status**: ✅ Planning Complete - Ready for Implementation
**Last Updated**: 2025-01-15
**Version**: 1.0
