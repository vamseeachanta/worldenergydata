# Drilling Expert Agent v3.0

## Overview
The Drilling Expert Agent is a specialized AI assistant with comprehensive domain knowledge in drilling engineering, well planning, drilling operations, and well construction. This agent implements v3.0 principles while providing expert guidance across onshore and offshore drilling operations.

## Specialization: Drilling Engineering
Domain expert in well planning, drilling operations, well control, and drilling optimization

## Core Capabilities

### Technical Domains
- **Well Planning & Design**: Trajectory design, casing programs, wellbore stability, anti-collision
- **Drilling Operations**: ROP optimization, hydraulics, directional drilling, MPD, automation
- **Drilling Equipment**: Rig systems, drill string, bits, downhole tools, surface equipment
- **Well Control & Safety**: Kick detection, well control methods, BOP systems, barrier management
- **Drilling Fluids**: WBM, OBM, specialty fluids, rheology, solids control, lost circulation
- **Specialized Operations**: Deepwater, HPHT, ERD, geothermal, CTD, casing drilling

### Analysis Expertise
- **Drilling Optimization**: ROP modeling, MSE analysis, parameter optimization
- **Hydraulics Calculations**: ECD, pressure losses, hole cleaning, surge/swab
- **Torque & Drag Analysis**: Soft/stiff string models, friction factors, buckling
- **Well Control Calculations**: Kill mud weight, MAASP, kick tolerance
- **Cost Analysis**: AFE preparation, time/depth curves, NPT analysis

## Features

### Phased Document Processing (v3.0)
- **Phase 1: Discovery** - Drilling document inventory and classification
- **Phase 2: Quality Assessment** - Technical document validation
- **Phase 3: Extraction** - Engineering knowledge extraction
- **Phase 4: Synthesis** - Best practices consolidation
- **Phase 5: Validation** - Industry standards compliance
- **Phase 6: Integration** - Knowledge base updating

### Modular Management (v3.0)
- **Specialization Level**: drilling-engineering
- **Context Optimization**: 16000 tokens
- **Refresh Priority**: medium
- **Auto-Refresh**: Enabled (7-day interval)

### Context Engineering (v2.0)
- **Layered Architecture**: Technical standards, operational procedures, lessons learned
- **Memory Management**: Offset well data, drilling parameters, incident history
- **RAG Optimization**: Technical document chunking, formula preservation
- **Duplicate Detection**: Report versioning, data deduplication

## Structure
```
drilling-expert/
├── agent.yaml                 # Agent configuration
├── context/                   # Context management
│   ├── domain/               # Drilling expertise
│   │   └── drilling_expertise.md
│   ├── repository/           # Code patterns
│   └── module/              # Module-specific docs
├── prompts/                 # Agent prompts
│   └── system_prompt.md    # Drilling expert prompt
├── templates/               # Calculation templates
│   └── drilling_calculations.py
├── processing/              # Phased processing
├── refresh/                # Refresh mechanisms
├── scratchpad/             # Temporary workspace
├── validation/             # Quality checks
└── README.md              # This file
```

## Usage Examples

### Well Planning
```python
# Trajectory design
"Design S-curve trajectory to 12000 ft MD with 8500 ft TVD target"
"Calculate minimum curvature path with 3°/100ft DLS limit"
"Perform anti-collision analysis with offset wells"

# Casing design
"Design casing program for HPHT well with 15 ppg pore pressure"
"Calculate burst and collapse for 9-5/8" casing at 10000 ft"
"Determine cement volume for 13-3/8" surface casing"

# Wellbore stability
"Analyze wellbore stability for shale section at 70° inclination"
"Calculate safe mud weight window from logs"
"Predict breakout width at current mud weight"
```

### Drilling Operations
```python
# ROP optimization
"Optimize WOB and RPM for maximum ROP in limestone"
"Calculate MSE and identify drilling dysfunction"
"Analyze founder point from drilling parameters"

# Hydraulics
"Calculate ECD at TD with current mud properties"
"Optimize flow rate for hole cleaning in horizontal section"
"Determine surge pressure while running casing"

# Directional drilling
"Calculate BHA tendency with current stabilizer placement"
"Design motor BHA for 8°/100ft build rate"
"Plan slide/rotate sequence for curve section"
```

### Well Control
```python
# Kick detection and control
"Calculate kill mud weight from SIDPP of 500 psi"
"Determine MAASP with current casing shoe depth"
"Analyze kick tolerance at current depth"

# Well control procedures
"Generate kill sheet for driller's method"
"Calculate volumetric method pressure schedule"
"Determine maximum pit gain before exceeding MAASP"

# BOP operations
"Calculate shear ram pressure for 5" drill pipe"
"Determine accumulator capacity requirements"
"Plan BOP test procedures for subsea stack"
```

### Code Generation
```python
# Using the templates
from agents.drilling_expert.templates.drilling_calculations import *

# ECD Calculation
ecd = calculate_ecd(
    mud_weight_ppg=12.5,
    annular_pressure_loss_psi=250,
    tvd_ft=10000
)
print(f"ECD: {ecd:.2f} ppg")

# MSE Analysis
mse = calculate_mse(
    wob_klbs=30,
    rpm=120,
    torque_ft_lbs=15000,
    rop_ft_hr=100,
    bit_diameter_in=8.5
)
print(f"MSE: {mse:,.0f} psi")

# Trajectory Calculation
trajectory = minimum_curvature_method(md_array, inc_array, azi_array)
print(f"TVD at TD: {trajectory['tvd'][-1]:.1f} ft")
```

## Integration with WorldEnergyData

### BSEE Drilling Data
- Well spud reports and drilling permits
- Drilling incident analysis and statistics
- Rig utilization and performance metrics
- Regulatory compliance tracking
- Safety performance indicators

### Performance Analytics
- ROP improvement tracking
- NPT reduction analysis
- Learning curve development
- Technology effectiveness evaluation
- Best practices identification

### Cost Management
- AFE vs actual cost tracking
- Cost per foot benchmarking
- NPT cost impact analysis
- Technology ROI evaluation
- Contract optimization

## Key Files

- **Domain Knowledge**: `context/domain/drilling_expertise.md`
- **System Prompt**: `prompts/system_prompt.md`
- **Calculations**: `templates/drilling_calculations.py`
- **Agent Config**: `agent.yaml`

## Best Practices

### When Using This Agent

1. **Provide Well Information**: Include key details
   - Well type (vertical, directional, horizontal)
   - Depths (MD, TVD, water depth if offshore)
   - Formation types and pressures
   - Rig capabilities
   - Environmental conditions

2. **Specify Constraints**: Be clear about limitations
   - Equipment ratings and capabilities
   - Regulatory requirements
   - Environmental restrictions
   - Time and cost constraints
   - Safety requirements

3. **Data Quality**: Ensure accurate inputs
   - Verify measurement units (ft, m, ppg, psi)
   - Check data consistency
   - Validate against offset wells
   - Document assumptions
   - Include uncertainty ranges

4. **Safety Focus**: Always prioritize
   - Well control readiness
   - Personnel safety
   - Environmental protection
   - Equipment integrity
   - Regulatory compliance

## Quality Standards

### All Drilling Analysis Must
1. Prioritize safety and well control
2. Use proven engineering methods
3. Consider operational feasibility
4. Follow industry standards (API, ISO)
5. Include risk assessment

### Critical Reminders
- Never compromise well control for speed
- Always verify barrier integrity
- Maintain two-barrier philosophy
- Follow MOC procedures for changes
- Document all decisions and deviations

### Professional Standards
- Apply API recommended practices
- Follow IADC guidelines
- Meet regulatory requirements
- Use industry best practices
- Maintain competency standards

## Specialized Capabilities

### Deepwater Drilling
- Riser analysis and management
- Shallow hazard assessment
- Dual gradient drilling design
- Subsea BOP operations
- Hydrate prevention strategies

### HPHT Wells
- Temperature and pressure management
- Equipment selection and derating
- Mud stability at extreme conditions
- Enhanced well control procedures
- Material selection guidelines

### Extended Reach Drilling
- Torque and drag modeling
- Hole cleaning optimization
- ECD management strategies
- Drill string fatigue analysis
- Friction reduction techniques

## Safety & Environment

### Well Control Priorities
1. Detect kicks early
2. Shut in properly
3. Calculate kill parameters
4. Execute kill procedures
5. Monitor and verify success

### Environmental Protection
- Prevent discharge of fluids
- Manage drilling waste
- Monitor air emissions
- Protect water resources
- Minimize ecological impact

## Metrics
- **Specialization**: drilling-engineering
- **Context Size**: 16000 tokens
- **Refresh Priority**: medium
- **Update Frequency**: Weekly (operations data)
- **Created**: 2025-08-25

---

*Enhanced Agent v3.0 - Comprehensive drilling engineering expertise with operational focus*