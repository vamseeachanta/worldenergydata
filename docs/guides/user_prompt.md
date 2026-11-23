# User Prompt - WorldEnergyData Analysis Suite

> **Status:** Approved
> **Created:** 2025-10-22
> **Last Updated:** 2025-10-22

---

## Objective

Create a comprehensive, standalone execution framework for worldenergydata repository that enables complete energy data analysis workflows (BSEE wells, Lower Tertiary fields, Marine Safety incidents) without dependence on AI agents. All analyses must be executable via clear bash scripts organized by module.

---

## Requirements

### Functional Requirements

1. **Standalone Execution**
   - All analysis workflows executable via bash scripts
   - No AI agent dependencies for execution
   - Clear, documented scripts organized by module
   - Single-command execution for complete analysis suites

2. **BSEE Analysis**
   - All wells production analysis
   - Lower Tertiary deepwater field analysis (Anchor, Julia, Jack, St. Malo)
   - FDAS-enhanced BSEE data processing
   - NPV (Net Present Value) economic evaluation
   - Interactive HTML reports with Plotly visualizations

3. **Marine Safety Analysis**
   - Comprehensive incident database analysis
   - Scenario-specific analyses (foundering, collision, fire, machinery, grounding, flooding)
   - Multi-source data integration (USCG, NOAA, MAIB, TSB)
   - AI-powered incident classification (optional)
   - Cause analysis and statistics

4. **Module Organization**
   - Scripts organized in `scripts/<module>/` directories
   - Module structure: bsee/, marine_safety/, production/, analysis/, imo/
   - Clear separation of concerns

### Non-Functional Requirements

1. **Performance**
   - Complete analysis suite executes in under 45 minutes
   - Individual module analyses complete in under 20 minutes
   - Efficient data processing with progress indicators

2. **Usability**
   - Comprehensive README documentation
   - Clear usage examples
   - Helpful error messages
   - Color-coded console output

3. **Maintainability**
   - Modular bash script architecture
   - YAML-based configuration
   - Consistent coding patterns
   - Well-commented code

---

## Constraints

### Technical Constraints
- Python 3.9+ required
- All visualizations must use interactive libraries (Plotly, Bokeh, Altair)
- No static matplotlib PNG/SVG exports
- CSV data import with relative paths only

### Business Constraints
- Use only public data sources (BSEE, USCG, NOAA, etc.)
- Open-source implementation
- No proprietary dependencies

### Time Constraints
- Complete suite must be executable immediately
- No manual intervention required during execution

---

## Input/Output Specification

### Input
- **Format:** YAML configuration files (optional)
- **Source:** `config/input/<module>.yaml`
- **Validation:** Schema validation via Python scripts
- **Size limits:** N/A (processes existing data files)

### Output
- **Format:** HTML (primary), CSV, JSON, Markdown
- **Destination:** `reports/<module>/` or custom directory
- **Content:** Interactive visualizations, data tables, summary statistics
- **Structure:** Organized by analysis suite and module

---

## Success Criteria

### Definition of Done
- [x] Master bash script (`run_all_analyses.sh`) executes complete suite
- [x] BSEE module scripts execute all wells and Lower Tertiary analyses
- [x] Marine Safety module scripts execute all incident scenarios
- [x] All scripts organized in `scripts/<module>/` directories
- [x] Comprehensive README documentation created
- [ ] YAML configuration files created for all workflows
- [ ] All scripts tested and executable standalone
- [ ] User prompt and pseudocode documentation complete

### Acceptance Tests

1. **Master Script Execution**
   - Given: Clean repository with data files
   - When: Execute `./scripts/run_all_analyses.sh`
   - Then: Complete analysis suite runs without errors, generates master summary report

2. **BSEE All Wells Analysis**
   - Given: BSEE production data available
   - When: Execute `./scripts/bsee/run_all_wells_analysis.sh`
   - Then: Generates production analysis, FDAS enhancement, and production reports

3. **Lower Tertiary Analysis**
   - Given: Lower Tertiary field data available
   - When: Execute `./scripts/bsee/run_lower_tertiary_analysis.sh`
   - Then: Generates field analysis, NPV calculations, and field-specific reports

4. **Marine Safety Analysis**
   - Given: Marine incident databases available
   - When: Execute `./scripts/marine_safety/run_all_incident_analysis.sh`
   - Then: Generates comprehensive incident analysis across all scenarios

---

## Edge Cases & Error Handling

### Edge Cases to Handle
1. Missing Python installation → Clear error message with installation instructions
2. Missing data files → Skip with warning, continue processing available data
3. Insufficient disk space → Detect and warn before processing
4. Missing dependencies → Provide pip/uv install command

### Error Scenarios
1. Python script failure → Log error, continue with remaining analyses
2. Data import failure → Log warning, skip that data source
3. Invalid YAML config → Use default configuration, log warning
4. Permission errors → Clear message about chmod +x requirements

---

## Dependencies

### External Systems
- BSEE public data APIs/files
- USCG MISLE database
- NOAA Marine Casualty data
- UK MAIB data
- Canadian TSB data

### Libraries/Frameworks
- pandas >= 2.0.0 (required)
- numpy >= 1.24.0 (required)
- plotly >= 5.14.0 (required)
- matplotlib >= 3.7.0 (required)
- numpy-financial >= 1.0.0 (required)
- pyyaml >= 6.0.0 (required)

---

## Examples

### Example Usage

```bash
# Execute complete analysis suite
./scripts/run_all_analyses.sh

# Execute with custom output directory
./scripts/run_all_analyses.sh /path/to/custom/output

# Execute specific module
./scripts/bsee/run_all_wells_analysis.sh
./scripts/bsee/run_lower_tertiary_analysis.sh
./scripts/marine_safety/run_all_incident_analysis.sh

# With custom output and config
./scripts/bsee/run_all_wells_analysis.sh /custom/output /custom/config.yaml
```

### Example Output Structure

```
reports/complete_analysis_20251022_140530/
├── ANALYSIS_SUMMARY.md
├── bsee/
│   ├── all_wells/
│   │   ├── production_analysis/
│   │   │   └── index.html
│   │   ├── fdas_enhanced/
│   │   └── production_reports/
│   │       └── index.html
│   └── lower_tertiary/
│       ├── field_analysis/
│       ├── npv_analysis/
│       │   └── index.html
│       └── fields/
│           ├── Anchor/index.html
│           ├── Julia/index.html
│           ├── Jack/index.html
│           └── St. Malo/index.html
├── marine_safety/
│   ├── database_analysis/
│   │   └── index.html
│   ├── scenarios/
│   │   ├── foundering/index.html
│   │   ├── collision/index.html
│   │   ├── fire/index.html
│   │   ├── machinery/index.html
│   │   ├── grounding/index.html
│   │   └── flooding/index.html
│   └── llm_classification/
└── production/
    └── fdas/
```

---

## Additional Context

This implementation follows the SPARC development workflow with AI Agent Orchestration for systematic development:

1. **Specification** - This user prompt defines requirements
2. **Pseudocode** - Algorithm design in `docs/pseudocode/`
3. **Architecture** - Module organization and bash script structure
4. **Refinement** - TDD implementation with pytest
5. **Completion** - Bash-based execution

All scripts must be AI-agent independent for production use while maintaining compatibility with AI-assisted development workflows.

---

## Change Log

| Date | Change Description | Reason |
|------|-------------------|---------|
| 2025-10-22 | Initial creation | User request for standalone bash execution framework |
| 2025-10-22 | Added module organization requirements | Clarify scripts/<module>/ structure |
| 2025-10-22 | Added comprehensive analysis suite | Complete BSEE + Marine Safety workflows |

---

**END OF USER PROMPT**
