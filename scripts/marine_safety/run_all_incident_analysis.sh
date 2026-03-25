#!/bin/bash
# ABOUTME: Execute comprehensive marine safety incident analysis
# ABOUTME: Analyzes various incident scenarios including foundering, collisions, fires, and mechanical failures

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/reports/marine_safety}"
CONFIG_FILE="${2:-$PROJECT_ROOT/config/input/marine_safety.yaml}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Marine Safety Incident Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓ Output directory: $OUTPUT_DIR${NC}"
echo ""

# Run comprehensive database analysis
echo -e "${YELLOW}Step 1: Analyzing complete marine safety database...${NC}"
python "$PROJECT_ROOT/scripts/analyze_marine_safety_database.py" \
    --output "$OUTPUT_DIR/database_analysis" \
    --format html \
    --interactive

echo -e "${GREEN}✓ Database analysis complete${NC}"
echo ""

# Run cause-specific analyses
echo -e "${YELLOW}Step 2: Analyzing incident causes and statistics...${NC}"

SCENARIOS=(
    "foundering:Foundering Incidents"
    "collision:Collision Analysis"
    "fire:Fire and Explosion"
    "machinery:Machinery Failure"
    "grounding:Grounding Incidents"
    "flooding:Flooding Events"
)

for SCENARIO in "${SCENARIOS[@]}"; do
    IFS=':' read -r TYPE NAME <<< "$SCENARIO"
    echo -e "  ${BLUE}→${NC} Analyzing $NAME..."

    python "$PROJECT_ROOT/examples/marine_safety_cause_visualization_demo.py" \
        --scenario "$TYPE" \
        --output "$OUTPUT_DIR/scenarios/$TYPE" \
        --format html \
        --interactive
done

echo -e "${GREEN}✓ Scenario analysis complete${NC}"
echo ""

# Run LLM classification demo (if available)
echo -e "${YELLOW}Step 3: Running AI-powered incident classification...${NC}"
if [ -f "$PROJECT_ROOT/examples/llm_classification_demo.py" ]; then
    python "$PROJECT_ROOT/examples/llm_classification_demo.py" \
        --output "$OUTPUT_DIR/llm_classification" \
        --format html \
        --interactive

    echo -e "${GREEN}✓ LLM classification complete${NC}"
else
    echo -e "${YELLOW}⚠ LLM classification script not found, skipping${NC}"
fi
echo ""

# Import additional data sources
echo -e "${YELLOW}Step 4: Importing data from additional safety databases...${NC}"

DATA_SOURCES=(
    "misle:USCG MISLE"
    "noaa:NOAA Marine Casualties"
    "maib:UK MAIB"
    "tsb:Canadian TSB"
)

for SOURCE in "${DATA_SOURCES[@]}"; do
    IFS=':' read -r TYPE NAME <<< "$SOURCE"
    IMPORT_SCRIPT="$PROJECT_ROOT/scripts/import_${TYPE}_data.py"

    if [ -f "$IMPORT_SCRIPT" ]; then
        echo -e "  ${BLUE}→${NC} Importing $NAME..."
        python "$IMPORT_SCRIPT" \
            --output "$OUTPUT_DIR/imports/$TYPE" \
            --format csv
    else
        echo -e "  ${YELLOW}⚠${NC} $NAME import script not found, skipping"
    fi
done

echo -e "${GREEN}✓ Data import complete${NC}"
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Marine Safety Analysis Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Results saved to: $OUTPUT_DIR${NC}"
echo ""
echo "Analysis components:"
echo "  • Database Analysis: $OUTPUT_DIR/database_analysis/"
echo "  • Incident Scenarios:"
echo "    - Foundering: $OUTPUT_DIR/scenarios/foundering/"
echo "    - Collisions: $OUTPUT_DIR/scenarios/collision/"
echo "    - Fire/Explosion: $OUTPUT_DIR/scenarios/fire/"
echo "    - Machinery: $OUTPUT_DIR/scenarios/machinery/"
echo "    - Grounding: $OUTPUT_DIR/scenarios/grounding/"
echo "    - Flooding: $OUTPUT_DIR/scenarios/flooding/"
echo "  • LLM Classification: $OUTPUT_DIR/llm_classification/"
echo "  • Data Imports: $OUTPUT_DIR/imports/"
echo ""
echo -e "${BLUE}View main dashboard:${NC}"
echo "  file://$OUTPUT_DIR/database_analysis/index.html"
