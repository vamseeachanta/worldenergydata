# WorldEnergyData Scripts

> Comprehensive execution scripts for all energy data analyses

## Quick Start

### Run Everything
```bash
# Execute complete analysis suite (BSEE + Marine Safety + Production)
./scripts/run_all_analyses.sh

# With custom output directory
./scripts/run_all_analyses.sh /path/to/output
```

### Run Specific Analysis Suites

#### BSEE Well Analysis
```bash
# All wells analysis
./scripts/bsee/run_all_wells_analysis.sh

# Lower Tertiary deepwater fields (Anchor, Julia, Jack, St. Malo)
./scripts/bsee/run_lower_tertiary_analysis.sh

# With custom output
./scripts/bsee/run_all_wells_analysis.sh /path/to/output
```

#### Marine Safety Analysis
```bash
# Complete incident analysis (all scenarios)
./scripts/marine_safety/run_all_incident_analysis.sh

# With custom output
./scripts/marine_safety/run_all_incident_analysis.sh /path/to/output
```

---

## Scripts Organization

```
scripts/
├── run_all_analyses.sh           # Master script - runs everything
├── bsee/                          # BSEE well and production analysis
│   ├── run_all_wells_analysis.sh
│   └── run_lower_tertiary_analysis.sh
├── marine_safety/                 # Marine incident analysis
│   └── run_all_incident_analysis.sh
├── analysis/                      # General analysis scripts
├── production/                    # Production-specific analysis
└── imo/                          # IMO data processing
```

---

## BSEE Analysis Scripts

### All Wells Analysis
**Script:** `scripts/bsee/run_all_wells_analysis.sh`

**What it does:**
- Analyzes production data for all BSEE wells
- Enhances BSEE data with FDAS (Field and Development Area System) information
- Generates comprehensive production reports with interactive visualizations

**Outputs:**
- Production analysis reports (HTML)
- FDAS-enhanced datasets
- Time-series production charts
- Well performance metrics

**Usage:**
```bash
./scripts/bsee/run_all_wells_analysis.sh [output_dir] [config_file]
```

**Example:**
```bash
./scripts/bsee/run_all_wells_analysis.sh ./reports/bsee_wells
```

---

### Lower Tertiary Analysis
**Script:** `scripts/bsee/run_lower_tertiary_analysis.sh`

**What it does:**
- Analyzes major Lower Tertiary deepwater fields:
  - Anchor Field
  - Julia Field
  - Jack Field
  - St. Malo Field
- Calculates NPV (Net Present Value) for economic evaluation
- Generates field-specific performance reports

**Outputs:**
- Field analysis reports (HTML)
- NPV calculations with sensitivity analysis
- Production forecasts
- Economic metrics (IRR, payback period, etc.)

**Usage:**
```bash
./scripts/bsee/run_lower_tertiary_analysis.sh [output_dir] [config_file]
```

**Example:**
```bash
./scripts/bsee/run_lower_tertiary_analysis.sh ./reports/lower_tertiary
```

**NPV Parameters:**
- Default discount rate: 10%
- Default oil price: $75/barrel
- Customize via config file

---

## Marine Safety Analysis Scripts

### All Incident Analysis
**Script:** `scripts/marine_safety/run_all_incident_analysis.sh`

**What it does:**
- Comprehensive analysis of marine safety incidents
- Analyzes multiple incident scenarios:
  - Foundering incidents
  - Collision analysis
  - Fire and explosion events
  - Machinery failures
  - Grounding incidents
  - Flooding events
- Imports data from multiple safety databases:
  - USCG MISLE
  - NOAA Marine Casualties
  - UK MAIB
  - Canadian TSB
- AI-powered incident classification (if available)

**Outputs:**
- Database-wide incident analysis (HTML)
- Scenario-specific reports with visualizations
- Cause analysis and statistics
- LLM classification results
- Integrated multi-source datasets

**Usage:**
```bash
./scripts/marine_safety/run_all_incident_analysis.sh [output_dir] [config_file]
```

**Example:**
```bash
./scripts/marine_safety/run_all_incident_analysis.sh ./reports/marine_safety
```

---

## Master Analysis Suite

### Complete Analysis
**Script:** `scripts/run_all_analyses.sh`

**What it does:**
- Runs ALL analysis suites in sequence:
  1. BSEE Well Analysis (all wells)
  2. BSEE Lower Tertiary Analysis
  3. Marine Safety Incident Analysis
  4. Production Analysis
- Generates master summary report
- Tracks execution time and system metrics

**Outputs:**
- Complete analysis suite in organized directory structure
- Master summary report (Markdown)
- Quick links to all dashboards
- Execution metrics and system information

**Usage:**
```bash
./scripts/run_all_analyses.sh [output_dir]
```

**Example:**
```bash
./scripts/run_all_analyses.sh ./reports/complete_analysis
```

**Default output structure:**
```
reports/complete_analysis_YYYYMMDD_HHMMSS/
├── ANALYSIS_SUMMARY.md          # Master summary
├── bsee/
│   ├── all_wells/
│   │   ├── production_analysis/
│   │   ├── fdas_enhanced/
│   │   └── production_reports/
│   └── lower_tertiary/
│       ├── field_analysis/
│       ├── npv_analysis/
│       └── fields/
│           ├── Anchor/
│           ├── Julia/
│           ├── Jack/
│           └── St. Malo/
├── marine_safety/
│   ├── database_analysis/
│   ├── scenarios/
│   │   ├── foundering/
│   │   ├── collision/
│   │   ├── fire/
│   │   ├── machinery/
│   │   ├── grounding/
│   │   └── flooding/
│   ├── llm_classification/
│   └── imports/
└── production/
    └── fdas/
```

---

## Prerequisites

### Required
- **Python 3.9+**
- **Required packages** (install via uv or pip):
  ```bash
  # Using UV (recommended)
  uv sync

  # Or using pip
  pip install -r requirements.txt
  ```

### Optional
- **UV** (faster package management)
- **YAML configuration files** (use defaults if not provided)

---

## Configuration

### YAML Configuration Files

Scripts can use YAML configuration files for customization:

```yaml
# config/input/bsee_all_wells.yaml
metadata:
  feature: "bsee-all-wells-analysis"
  created: "2025-10-22"

requirements:
  input:
    - type: "bsee_production_data"
    - path_type: "relative"

  processing:
    - analyze_production: true
    - generate_reports: true

  output:
    - format: "html"
    - visualization: "plotly"
    - interactive: true
```

Place custom configurations in `config/input/` directory.

---

## Output Formats

All scripts support multiple output formats:

- **HTML** - Interactive reports (default)
- **CSV** - Raw data exports
- **JSON** - Structured data exports
- **Markdown** - Summary reports

Interactive HTML reports include:
- Plotly visualizations (hover, zoom, pan)
- Responsive design
- Export to PNG/SVG
- Data tables with filtering

---

## Execution Time

Approximate execution times (varies by data size):

- **All Wells Analysis:** 5-15 minutes
- **Lower Tertiary Analysis:** 3-8 minutes
- **Marine Safety Analysis:** 10-20 minutes
- **Complete Analysis Suite:** 20-45 minutes

---

## Troubleshooting

### Python not found
```bash
# Install Python 3.9+
# On Ubuntu/Debian:
sudo apt install python3.9 python3-pip

# On macOS:
brew install python@3.9
```

### Missing dependencies
```bash
# Install via UV (recommended)
uv sync

# Or via pip
pip install pandas numpy plotly matplotlib numpy-financial pyyaml
```

### Permission denied
```bash
# Make scripts executable
chmod +x scripts/*.sh
chmod +x scripts/bsee/*.sh
chmod +x scripts/marine_safety/*.sh
```

### Script fails partway through
- Check the error message carefully
- Ensure all required data files are present
- Verify Python package versions
- Check available disk space for large reports

---

## Data Sources

Scripts process data from:

- **BSEE** - Bureau of Safety and Environmental Enforcement
- **FDAS** - Field and Development Area System
- **USCG MISLE** - US Coast Guard Marine Information
- **NOAA** - National Oceanic and Atmospheric Administration
- **MAIB** - UK Marine Accident Investigation Branch
- **TSB** - Transportation Safety Board of Canada

---

## Support

For issues or questions:
- Check script output for error messages
- Review prerequisites and dependencies
- Consult individual script headers for details
- Check `docs/` directory for additional documentation

---

## Development Workflow

These scripts follow the **SPARC Development Workflow**:

1. **User Prompt** - Requirements in `user_prompt.md`
2. **YAML Config** - Structured configuration in `config/input/`
3. **Pseudocode** - Algorithm design in `docs/pseudocode/`
4. **TDD** - Test-driven development
5. **Implementation** - Modular Python code in `src/`
6. **Bash Execution** - Single-command execution

See `docs/DEVELOPMENT_WORKFLOW.md` for complete workflow documentation.

---

**Last Updated:** 2025-10-22
**Version:** 1.0.0

## Pack lint

```bash
python scripts/pack_lint.py --account "$GITHUB_REPOSITORY_OWNER" path/to/agent-pack.md
python scripts/pack_lint.py --account "$GITHUB_REPOSITORY_OWNER" --drafts path/to/drafts.md path/to/agent-pack.md
```

The script is run by the pull-request check and before a pack is published.
It uses only the Python standard library and accepts multiple pack paths.

- `S10`: headings cover sections 1 through 10, with a space after the hashes; fenced headings do not count.
- `SWEEP`: include `sweep: N found` outside fenced code; zero findings require the grep used alongside it.
- `NODE`: test node IDs start with `tests/` or contain `/tests/`; source-symbol references are allowed.
- `URL`: omit GitHub API, issue and pull-request URLs and owner names in URLs; write `#NNN` for an issue of this repository; for another project use link text, not `#NNN`.
- `DRAFT`: number each pending issue; `--drafts FILE` also checks its list entry, formatted `Draft N: <subject>` (case-insensitive; heading, list and bold marks before it are allowed).
- `ROLE`: use `maintainer` when a merging subject ends in a coordination role noun; change nouns and ordinary engineering prose pass. Use `maintainers` for coordination.
- `TABLE`: keep table rows together; separate complete tables and fenced examples are allowed.
- `READ`: an unreadable pack, including invalid UTF-8, fails.

Exit codes: `0` clean, `1` lint/read failure, `2` usage error.
The optional `--skip RULE[,RULE]` filters named lint rules locally; CI uses no skips.
Without `--drafts`, numbered pending issues produce a note because list matching is unavailable.
Without a non-empty `--account` or `GITHUB_REPOSITORY_OWNER`, the account-name URL check is skipped with one warning on stderr per run; issue and pull-request URLs are still checked, and the warning does not change the exit status.
The check covers mechanical wording and structure; it does not qualify technical evidence.
