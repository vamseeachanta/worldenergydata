#!/bin/bash
# ABOUTME: Master execution script for all worldenergydata analyses
# ABOUTME: Runs complete BSEE, Marine Safety, and other energy data workflows

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/reports/complete_analysis_$(date +%Y%m%d_%H%M%S)}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}WorldEnergyData Complete Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${BLUE}Timestamp: $(date)${NC}"
echo -e "${BLUE}Output Directory: $OUTPUT_DIR${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python &> /dev/null; then
    echo -e "${RED}✗ Python not found${NC}"
    echo "Please install Python 3.9+ and try again"
    exit 1
fi

PYTHON_VERSION=$(python --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}⚠ UV not found (optional, using pip)${NC}"
else
    UV_VERSION=$(uv --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ UV $UV_VERSION${NC}"
fi

echo ""

# Create master output directory
mkdir -p "$OUTPUT_DIR"

# Track execution time
START_TIME=$(date +%s)

# Analysis Suite 1: BSEE Analysis
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Suite 1: BSEE Well Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

BSEE_OUTPUT="$OUTPUT_DIR/bsee"
mkdir -p "$BSEE_OUTPUT"

echo -e "${YELLOW}1.1: All Wells Analysis${NC}"
bash "$SCRIPT_DIR/bsee/run_all_wells_analysis.sh" "$BSEE_OUTPUT/all_wells"
echo ""

echo -e "${YELLOW}1.2: Lower Tertiary Analysis${NC}"
bash "$SCRIPT_DIR/bsee/run_lower_tertiary_analysis.sh" "$BSEE_OUTPUT/lower_tertiary"
echo ""

# Analysis Suite 2: Marine Safety
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Suite 2: Marine Safety Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

MARINE_OUTPUT="$OUTPUT_DIR/marine_safety"
mkdir -p "$MARINE_OUTPUT"

echo -e "${YELLOW}2.1: Complete Incident Analysis${NC}"
bash "$SCRIPT_DIR/marine_safety/run_all_incident_analysis.sh" "$MARINE_OUTPUT"
echo ""

# Analysis Suite 3: Production Analysis
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Suite 3: Production Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

PRODUCTION_OUTPUT="$OUTPUT_DIR/production"
mkdir -p "$PRODUCTION_OUTPUT"

echo -e "${YELLOW}3.1: FDAS Production Retrieval${NC}"
if [ -f "$SCRIPT_DIR/run_fdas_production_retrieval.py" ]; then
    python "$SCRIPT_DIR/run_fdas_production_retrieval.py" \
        --output "$PRODUCTION_OUTPUT/fdas" \
        --format html \
        --interactive
    echo -e "${GREEN}✓ FDAS production analysis complete${NC}"
else
    echo -e "${YELLOW}⚠ FDAS script not found, skipping${NC}"
fi
echo ""

# Calculate total execution time
END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
MINUTES=$((DURATION / 60))
SECONDS=$((DURATION % 60))

# Generate master summary report
SUMMARY_FILE="$OUTPUT_DIR/ANALYSIS_SUMMARY.md"
cat > "$SUMMARY_FILE" << EOF
# WorldEnergyData Complete Analysis Summary

**Execution Date:** $(date)
**Total Duration:** ${MINUTES}m ${SECONDS}s
**Output Directory:** $OUTPUT_DIR

---

## Analysis Suites Completed

### 1. BSEE Well Analysis
- **All Wells Analysis:** $BSEE_OUTPUT/all_wells/
- **Lower Tertiary Analysis:** $BSEE_OUTPUT/lower_tertiary/

Key Outputs:
- Production data analysis for all BSEE wells
- NPV analysis for Lower Tertiary fields (Anchor, Julia, Jack, St. Malo)
- FDAS-enhanced BSEE data
- Comprehensive production reports

### 2. Marine Safety Analysis
- **Complete Incident Analysis:** $MARINE_OUTPUT/

Key Outputs:
- Database-wide incident analysis
- Scenario-specific analyses (foundering, collision, fire, machinery, grounding, flooding)
- LLM-powered incident classification
- Multi-source data integration (USCG, NOAA, MAIB, TSB)

### 3. Production Analysis
- **FDAS Production:** $PRODUCTION_OUTPUT/fdas/

Key Outputs:
- Field-specific production retrieval
- Historical production trends
- Economic analysis

---

## Quick Links

### Main Dashboards
- BSEE All Wells: file://$BSEE_OUTPUT/all_wells/production_reports/index.html
- Lower Tertiary NPV: file://$BSEE_OUTPUT/lower_tertiary/npv_analysis/index.html
- Marine Safety: file://$MARINE_OUTPUT/database_analysis/index.html

### Field-Specific Reports
- Anchor Field: file://$BSEE_OUTPUT/lower_tertiary/fields/Anchor/index.html
- Julia Field: file://$BSEE_OUTPUT/lower_tertiary/fields/Julia/index.html
- Jack Field: file://$BSEE_OUTPUT/lower_tertiary/fields/Jack/index.html
- St. Malo Field: file://$BSEE_OUTPUT/lower_tertiary/fields/St. Malo/index.html

### Incident Scenarios
- Foundering: file://$MARINE_OUTPUT/scenarios/foundering/index.html
- Collisions: file://$MARINE_OUTPUT/scenarios/collision/index.html
- Fire/Explosion: file://$MARINE_OUTPUT/scenarios/fire/index.html
- Machinery Failure: file://$MARINE_OUTPUT/scenarios/machinery/index.html

---

## Data Sources

- **BSEE:** Bureau of Safety and Environmental Enforcement
- **USCG MISLE:** US Coast Guard Marine Information for Safety and Law Enforcement
- **NOAA:** National Oceanic and Atmospheric Administration
- **MAIB:** UK Marine Accident Investigation Branch
- **TSB:** Transportation Safety Board of Canada

---

## System Information

- Python Version: $PYTHON_VERSION
- Execution Environment: $(uname -s) $(uname -r)
- Hostname: $(hostname)

EOF

# Final summary to console
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Complete Analysis Finished!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}✓ All analyses completed successfully${NC}"
echo -e "${BLUE}Total execution time: ${MINUTES}m ${SECONDS}s${NC}"
echo ""
echo -e "${YELLOW}Results Location:${NC}"
echo "  $OUTPUT_DIR"
echo ""
echo -e "${YELLOW}Summary Report:${NC}"
echo "  $SUMMARY_FILE"
echo ""
echo -e "${BLUE}Main Dashboards:${NC}"
echo "  • BSEE All Wells: file://$BSEE_OUTPUT/all_wells/production_reports/index.html"
echo "  • Lower Tertiary: file://$BSEE_OUTPUT/lower_tertiary/npv_analysis/index.html"
echo "  • Marine Safety: file://$MARINE_OUTPUT/database_analysis/index.html"
echo ""
echo -e "${GREEN}Analysis suite complete! 🚀${NC}"
