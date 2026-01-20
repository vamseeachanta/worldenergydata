# Oil and Gas Domain Expertise

## Core Competencies

### 1. Reservoir Engineering
- **Reservoir Characterization**: Porosity, permeability, saturation analysis
- **Reserve Estimation**: Volumetric, material balance, decline curve analysis
- **Reservoir Simulation**: Black oil, compositional, thermal modeling
- **Enhanced Oil Recovery (EOR)**: Chemical, thermal, gas injection methods
- **PVT Analysis**: Fluid properties, phase behavior, EOS modeling

### 2. Production Engineering
- **Well Performance**: IPR/VLP analysis, nodal analysis
- **Artificial Lift Systems**: ESP, gas lift, rod pumps, PCP, jet pumps
- **Production Optimization**: Rate allocation, production scheduling
- **Well Testing**: Pressure transient analysis, buildup/drawdown tests
- **Flow Assurance**: Hydrates, wax, asphaltenes, scale management

### 3. Drilling Engineering
- **Well Planning**: Trajectory design, casing design, mud programs
- **Drilling Operations**: ROP optimization, hole cleaning, stuck pipe prevention
- **Directional Drilling**: MWD/LWD, geosteering, horizontal wells
- **Well Control**: Kick detection, kill procedures, BOP systems
- **Drilling Fluids**: Mud properties, rheology, filtration control

### 4. Completion Engineering
- **Completion Design**: Open hole, cased hole, multilateral completions
- **Sand Control**: Gravel packs, screens, chemical consolidation
- **Stimulation**: Hydraulic fracturing, matrix acidizing, acid fracturing
- **Perforating**: Charge selection, underbalance design, oriented perforating
- **Smart Wells**: ICVs, downhole monitoring, intelligent completions

### 5. Facilities Engineering
- **Separation Systems**: Two/three phase separators, slug catchers
- **Processing Equipment**: Dehydration, sweetening, NGL recovery
- **Compression Systems**: Reciprocating, centrifugal compressors
- **Pipeline Design**: Hydraulics, material selection, corrosion control
- **Storage Facilities**: Tank design, vapor recovery, custody transfer

### 6. Offshore Engineering
- **Platform Types**: Fixed, floating (FPSO, TLP, SPAR, Semi-sub)
- **Subsea Systems**: Trees, manifolds, pipelines, umbilicals
- **Riser Systems**: SCR, TTR, flexible risers, hybrid systems
- **Mooring Systems**: Spread mooring, turret mooring, DP systems
- **Installation Methods**: Heavy lift, float-over, J-lay, S-lay, reel-lay

## Industry Standards & Regulations

### API Standards
- **API RP 2A-WSD**: Fixed offshore platforms
- **API RP 14E**: Offshore production systems
- **API RP 14C**: Safety systems for offshore production
- **API 6A**: Wellhead and christmas tree equipment
- **API 17 Series**: Subsea production systems

### International Standards
- **ISO 19900 Series**: Petroleum and natural gas industries - Offshore structures
- **ISO 13703**: Design and installation of piping systems on offshore platforms
- **NORSOK Standards**: Norwegian petroleum industry standards
- **DNV Standards**: Classification and certification

### Regulatory Compliance
- **BSEE (US)**: Bureau of Safety and Environmental Enforcement
- **HSE (UK)**: Health and Safety Executive
- **PSA (Norway)**: Petroleum Safety Authority
- **NOPSEMA (Australia)**: National Offshore Petroleum Safety Authority

## Key Analysis Methods

### Economic Evaluation
- **NPV/IRR Analysis**: Project economics, sensitivity analysis
- **Decline Curve Analysis**: Arps equations, type curves
- **Monte Carlo Simulation**: Risk assessment, probabilistic forecasting
- **Real Options Valuation**: Investment timing, abandonment options

### Technical Analysis
- **Material Balance**: Tank models, aquifer models, gas cap expansion
- **Pressure Transient Analysis**: Well test interpretation, skin factor
- **Rate Transient Analysis**: Production data analysis, EUR estimation
- **Network Modeling**: Integrated production system optimization

## Software Tools & APIs

### Reservoir Simulation
- **Eclipse**: Black oil and compositional simulation
- **CMG**: IMEX, GEM, STARS simulators
- **Petrel**: Integrated reservoir modeling
- **tNavigator**: Dynamic reservoir simulation

### Production Engineering
- **PROSPER**: Well performance analysis
- **GAP**: Production network optimization
- **PIPESIM**: Flow assurance and production systems
- **OLGA**: Dynamic multiphase flow simulation

### Data Management
- **WITSML**: Wellsite information transfer standard
- **PRODML**: Production data standards
- **RESQML**: Reservoir characterization markup language
- **PPDM**: Professional petroleum data management

## Python Libraries for Oil & Gas

### Core Libraries
```python
# Data Analysis
import pandas as pd
import numpy as np
import scipy.optimize

# Visualization
import matplotlib.pyplot as plt
import plotly.graph_objects as go

# Machine Learning
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

# Domain-Specific
import lasio  # LAS file reading
import welly  # Well log analysis
import striplog  # Lithology and stratigraphy
```

### Custom Modules
```python
# Decline curve analysis
from worldenergydata.modules.decline_curves import arps_decline

# PVT correlations
from worldenergydata.modules.pvt import standing_correlation

# Material balance
from worldenergydata.modules.material_balance import tank_model

# Economics
from worldenergydata.modules.economics import npv_analysis
```

## Integration with WorldEnergyData

### BSEE Module
- Production data analysis
- Safety incident tracking
- Regulatory compliance reporting
- Well performance monitoring

### Energy Markets
- Oil price forecasting
- Supply/demand analysis
- Market volatility assessment
- Trading strategy optimization

### Environmental Impact
- Emissions monitoring
- Carbon footprint analysis
- Sustainability metrics
- ESG reporting

## Best Practices

### Data Quality
1. Always validate input data ranges
2. Check for missing or anomalous values
3. Apply appropriate data cleaning techniques
4. Document data sources and assumptions

### Analysis Workflow
1. Start with exploratory data analysis
2. Apply domain-specific correlations
3. Validate results against field analogues
4. Perform sensitivity analysis
5. Document uncertainties

### Safety & Environment
1. Follow HSE guidelines
2. Consider environmental impact
3. Apply risk assessment methodologies
4. Maintain regulatory compliance

### Code Standards
1. Use industry-standard units (field/SI)
2. Include unit conversions
3. Implement error handling
4. Provide comprehensive documentation
5. Follow PEP 8 style guide

## Common Calculations

### Volumetrics
```python
STOIIP = 7758 * A * h * phi * (1 - Sw) / Boi  # STB
GIIP = 43560 * A * h * phi * (1 - Sw) / Bgi   # SCF
```

### Decline Curves
```python
# Exponential decline
q = qi * exp(-D * t)

# Hyperbolic decline
q = qi / (1 + b * D * t)**(1/b)

# Harmonic decline (b=1)
q = qi / (1 + D * t)
```

### Material Balance
```python
# General material balance equation
F = N * Et + We - Wp * Bw
where:
F = Underground withdrawal
Et = Total expansion
We = Water influx
```

## References

1. **Petroleum Engineering Handbook** - SPE
2. **Reservoir Engineering Handbook** - Tarek Ahmed
3. **Production Optimization Using Nodal Analysis** - Beggs
4. **Applied Petroleum Reservoir Engineering** - Craft & Hawkins
5. **Fundamentals of Reservoir Engineering** - Dake