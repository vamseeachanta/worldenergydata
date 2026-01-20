# Oil and Gas Expert Agent v3.0

## Overview
The Oil and Gas Expert Agent is a specialized AI assistant with comprehensive domain knowledge in petroleum engineering, reservoir analysis, production optimization, and energy industry operations. This agent implements mandatory v3.0 principles while providing expert guidance across the entire oil and gas value chain.

## Specialization: Oil and Gas Engineering
Domain expert in petroleum engineering, reservoir analysis, production systems, and energy operations

## Core Capabilities

### Technical Domains
- **Reservoir Engineering**: Characterization, simulation, reserves, EOR methods
- **Production Engineering**: Well performance, artificial lift, flow assurance
- **Drilling Engineering**: Well planning, directional drilling, well control
- **Completion Engineering**: Stimulation, sand control, smart wells
- **Facilities Engineering**: Processing, compression, pipeline systems
- **Offshore Engineering**: Platforms, subsea systems, risers, mooring

### Analysis Expertise
- **Economic Evaluation**: NPV/IRR, project economics, risk assessment
- **Data Analysis**: Production analysis, decline curves, forecasting
- **Technical Modeling**: Reservoir simulation, network optimization
- **Regulatory Compliance**: API, ISO, BSEE standards

## Features

### Phased Document Processing (v3.0)
- **Phase 1: Discovery** - Oil & gas document inventory
- **Phase 2: Quality Assessment** - Technical document prioritization
- **Phase 3: Extraction** - Engineering knowledge extraction
- **Phase 4: Synthesis** - Technical standards consolidation
- **Phase 5: Validation** - Industry compliance checks
- **Phase 6: Integration** - Domain knowledge integration

### Modular Management (v3.0)
- **Specialization Level**: petroleum-engineering
- **Context Optimization**: 16000 tokens
- **Refresh Priority**: low
- **Auto-Refresh**: Enabled (7-day interval)

### Context Engineering (v2.0)
- **Layered Architecture**: Domain expertise, operational procedures, field data
- **Memory Management**: Project history and technical decisions
- **RAG Optimization**: Technical document chunking strategies
- **Duplicate Detection**: Engineering data deduplication

## Structure
```
oil-and-gas-expert/
├── agent.yaml                 # Agent configuration
├── processing/               # Phased processing
│   ├── phases/              # Phase results
│   ├── metrics/             # Processing metrics
│   └── phase_status.yaml    # Current status
├── context/                 # Context management
│   ├── docs_registry.yaml   # Documentation registry
│   ├── chunk_index.json     # Chunk index
│   ├── module/              # Module-specific docs
│   ├── submodule/           # Submodule-specific docs
│   └── [other layers]/      # Context layers
├── refresh/                 # Refresh mechanisms
├── prompts/                 # Agent prompts
├── templates/               # Reusable templates
├── tools/                   # Custom tools
├── scratchpad/              # Temporary workspace
└── validation/              # Quarantine and validation
```

## Usage Examples

### Technical Consultations
```python
# Reservoir Engineering
"Calculate STOIIP for a reservoir with 500 acres, 50 ft pay, 25% porosity"
"Design water injection pattern for a 5-spot flood"
"Recommend EOR method for heavy oil reservoir"

# Production Engineering  
"Optimize ESP design for 5000 ft well with 2000 BOPD target"
"Diagnose production decline in gas lifted wells"
"Design separator for 30,000 BOPD with 40% water cut"

# Economic Analysis
"Calculate project NPV with $70/bbl oil price"
"Perform decline curve analysis on production data"
"Evaluate drilling economics for horizontal well"
```

### Integration with WorldEnergyData
```python
# BSEE Data Analysis
"Analyze Gulf of Mexico production trends from BSEE data"
"Generate safety compliance report for Platform A"
"Track well abandonment statistics by operator"

# Market Analysis
"Correlate production with WTI price movements"
"Forecast regional supply based on rig count"
"Analyze price volatility impact on project economics"
```

### Code Generation
```python
# Request implementations
"Generate Python code for material balance calculations"
"Create decline curve analysis script with Arps equations"
"Build PVT correlations library for black oil"
```

## Administration

### Process Documents (Phased Approach)
```bash
python create_module_agent.py oil-and-gas-expert --mode update \
  --process-docs "/path/to/technical/docs" --phased --module petroleum
```

### Refresh Agent Knowledge
```bash
python create_module_agent.py oil-and-gas-expert --mode refresh
```

### Add Technical Documentation
```bash
python create_module_agent.py oil-and-gas-expert --mode update \
  --add-doc ./docs/api_standards.pdf --category domain --title "API Standards"
```

### Check Agent Health
```bash
python create_module_agent.py oil-and-gas-expert --mode update --health-check
```

## Key Files
- **Domain Knowledge**: `context/domain/oil_gas_expertise.md`
- **System Prompt**: `prompts/system_prompt.md`
- **Agent Config**: `agent.yaml`
- **Processing Status**: `processing/phase_status.yaml`

## Metrics
- **Specialization**: petroleum-engineering
- **Context Size**: 16000 tokens  
- **Refresh Priority**: low
- **Created**: 2025-08-25

---
*Enhanced Agent v3.0 - Implementing mandatory phased processing and modular management*
