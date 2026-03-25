#!/bin/bash
# ABOUTME: Marine safety incident analysis runner
# ABOUTME: Analyzes hatch maloperation, foundering, and fatality incidents using LLM

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Marine Safety Incident Analysis ===${NC}"
echo ""

# Check if running from repository root
if [ ! -f "pyproject.toml" ]; then
    echo -e "${RED}Error: Please run this script from the repository root${NC}"
    echo "Usage: bash scripts/marine_safety/analyze_incidents.sh"
    exit 1
fi

# Create output directory (no timestamp - use consistent location)
OUTPUT_DIR="reports/marine_safety"
mkdir -p "$OUTPUT_DIR"

echo -e "${YELLOW}Output directory: ${OUTPUT_DIR}${NC}"
echo -e "${YELLOW}Note: Reports will overwrite previous analysis${NC}"
echo ""

# Check for LLM dependencies
echo -e "${YELLOW}Checking LLM dependencies...${NC}"
if python3 -c "import transformers" 2>/dev/null; then
    echo -e "${GREEN}✓ LLM dependencies installed${NC}"
    USE_LLM=true
else
    echo -e "${YELLOW}⚠ LLM dependencies not installed. Using regex detection.${NC}"
    echo -e "${YELLOW}  Install with: pip install worldenergydata[llm]${NC}"
    USE_LLM=false
fi
echo ""

# Run the analysis
echo -e "${GREEN}Running marine safety incident analysis...${NC}"
echo -e "${YELLOW}Analyzing all real incident data from:${NC}"
echo "  - Canadian TSB (86K+ incidents)"
echo "  - DLP Historical (93K+ incidents)"
echo "  - IMO GISIS (14K+ incidents)"
echo ""

python3 scripts/marine_safety/generate_incident_report.py \
    --output-dir "$OUTPUT_DIR" \
    --use-llm "$USE_LLM"

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=== Analysis Complete ===${NC}"
    echo ""
    echo -e "${GREEN}Reports generated in: ${OUTPUT_DIR}${NC}"
    echo ""
    echo "View the executive summary:"
    echo -e "${YELLOW}  file://${PWD}/${OUTPUT_DIR}/executive_summary.html${NC}"
    echo ""
    echo "View detailed reports:"
    echo "  - Hatch/Door Opening Analysis: ${OUTPUT_DIR}/hatch_analysis.html"
    echo "  - Foundering Analysis: ${OUTPUT_DIR}/foundering_analysis.html"
    echo "  - Fatality Analysis: ${OUTPUT_DIR}/fatality_analysis.html"
    echo ""
    echo -e "${GREEN}Note: Reports now include all door and opening incidents (hatches, doors, covers)${NC}"
    echo ""
else
    echo -e "${RED}Error: Analysis failed with exit code ${EXIT_CODE}${NC}"
    exit $EXIT_CODE
fi
