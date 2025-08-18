# Spec Requirements Document

> Spec: Fatigue S-N Curve Database for Oil & Gas Materials
> Created: 2025-08-16
> Status: Planning

## Overview

Create a comprehensive database of fatigue S-N curve data for various materials used in the oil and gas industry, collected from authoritative engineering standards (API, DNV, ISO, ABS, etc.). This database will provide engineering-quality fatigue life data in a standardized, machine-readable format for use by analysis tools like digitalmodel and other engineering repositories.

### Future Update Prompt

For future modifications to this spec, use the following prompt:
```
Update the fatigue S-N curve database spec to include:
- Additional material standards and specifications
- New curve fitting models (Basquin, Coffin-Manson, etc.)
- Environmental correction factors (seawater, temperature)
- Mean stress correction methods (Goodman, Gerber, etc.)
- Fatigue crack growth data (Paris law parameters)
- Integration with FEA software formats
Maintain compatibility with existing data structure and preserve all current material datasets.
```

## User Stories

### Structural Engineer Fatigue Analysis

As a **Structural Engineer**, I want to access standardized S-N curve data for various steel grades and weld classifications, so that I can perform fatigue life assessments for offshore structures according to industry standards.

The engineer imports S-N curve data for specific material grades (e.g., API 2W Grade 50, DNV C1 weld class) from the database. They use this data in their fatigue analysis software to calculate cumulative damage using rainflow counting and Miner's rule. The standardized format allows direct integration with tools like digitalmodel, OrcaFlex, or custom Python scripts. Having all relevant standards in one place eliminates manual digitization of curves from PDFs and reduces errors in fatigue calculations.

### Materials Specialist Verification

As a **Materials Specialist**, I want to compare S-N curves from different standards for the same material, so that I can select the most appropriate fatigue data for specific applications and validate design assumptions.

The specialist queries the database for all available S-N curves for a specific material (e.g., carbon steel in seawater). They compare curves from API RP 2A, DNV-RP-C203, ISO 19902, and ABS guidelines to understand conservatism levels and applicability ranges. The database provides metadata about test conditions, stress ratios, and environmental factors, enabling informed decisions about which curve to use for different design scenarios.

### Research Engineer Data Integration

As a **Research Engineer**, I want to programmatically access S-N curve parameters through a Python API, so that I can integrate fatigue data into automated design optimization and reliability analysis workflows.

The researcher uses the Python API to fetch S-N curve parameters (e.g., log N = log A - m × log S) for multiple materials. They integrate this data into Monte Carlo simulations for probabilistic fatigue assessment, considering material variability and loading uncertainty. The standardized data structure enables batch processing of multiple design cases and sensitivity studies on material selection.

## Spec Scope

1. **Data Collection Framework** - System to extract and digitize S-N curves from industry standards documents
2. **Standardized Data Model** - Unified schema for S-N curve parameters, metadata, and test conditions
3. **Material Classification System** - Hierarchical organization by material type, grade, and condition
4. **Standards Coverage** - Implementation of curves from API, DNV, ISO, ABS, and other recognized sources
5. **Python API Interface** - Programmatic access to query, filter, and retrieve S-N curve data
6. **Data Validation System** - Quality checks to ensure engineering accuracy and standard compliance
7. **Export Functionality** - Multiple output formats (JSON, CSV, HDF5) for integration with analysis tools

## Out of Scope

- Fatigue crack growth data (da/dN curves)
- Time-dependent fatigue (creep-fatigue interaction)
- Multiaxial fatigue criteria
- Fatigue testing or experimental data generation
- FEA integration plugins or solvers
- Web-based visualization interface
- Real-time data updates from standards bodies
- Proprietary or confidential material data

## Expected Deliverable

1. **Structured database** containing S-N curves from major oil & gas standards with complete metadata
2. **Python module** with API for querying and retrieving S-N curve data programmatically
3. **Data validation report** showing compliance with original standard sources and accuracy verification
4. **Documentation** including data sources, assumptions, and usage guidelines for engineering applications
5. **Integration examples** demonstrating use with digitalmodel repository and other analysis tools

## Spec Documentation

- Tasks: @specs/fatigue-sn-curve-database/tasks.md
- Technical Specification: @specs/fatigue-sn-curve-database/sub-specs/technical-spec.md
- API Specification: @specs/fatigue-sn-curve-database/sub-specs/api-spec.md
- Database Schema: @specs/fatigue-sn-curve-database/sub-specs/database-schema.md
- Tests Specification: @specs/fatigue-sn-curve-database/sub-specs/tests.md