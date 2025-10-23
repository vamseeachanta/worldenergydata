#!/bin/bash
# ABOUTME: Execute Lower Tertiary deepwater field analysis with NPV calculations
# ABOUTME: Analyzes Anchor, Julia, Jack, and St. Malo fields with economic modeling

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/reports/bsee/lower_tertiary}"
CONFIG_FILE="${2:-$PROJECT_ROOT/config/input/lower_tertiary.yaml}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Lower Tertiary Field Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python not found${NC}"
    exit 1
fi

mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓ Output directory: $OUTPUT_DIR${NC}"
echo ""

# Run Lower Tertiary analysis
echo -e "${YELLOW}Step 1: Analyzing Lower Tertiary fields (Anchor, Julia, Jack, St. Malo)...${NC}"
python "$PROJECT_ROOT/scripts/lower_tertiary_analysis.py" \
    --output "$OUTPUT_DIR/field_analysis" \
    --format html \
    --interactive

echo -e "${GREEN}✓ Field analysis complete${NC}"
echo ""

# Run NPV analysis
echo -e "${YELLOW}Step 2: Calculating NPV for Lower Tertiary fields...${NC}"
python "$PROJECT_ROOT/scripts/analyze_lower_tertiary_npv.py" \
    --output "$OUTPUT_DIR/npv_analysis" \
    --format html \
    --interactive \
    --discount-rate 0.10 \
    --oil-price 75.0

echo -e "${GREEN}✓ NPV analysis complete${NC}"
echo ""

# Run field-specific reports
echo -e "${YELLOW}Step 3: Generating field-specific reports...${NC}"

for FIELD in "Anchor" "Julia" "Jack" "St. Malo"; do
    echo -e "  ${BLUE}→${NC} Generating report for $FIELD..."
    python "$PROJECT_ROOT/scripts/generate_field_report.py" \
        --field "$FIELD" \
        --output "$OUTPUT_DIR/fields/$FIELD" \
        --format html \
        --interactive
done

echo -e "${GREEN}✓ Field reports generated${NC}"
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Lower Tertiary Analysis Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Results saved to: $OUTPUT_DIR${NC}"
echo ""
echo "Analysis components:"
echo "  • Field Analysis: $OUTPUT_DIR/field_analysis/"
echo "  • NPV Analysis: $OUTPUT_DIR/npv_analysis/"
echo "  • Anchor Field: $OUTPUT_DIR/fields/Anchor/"
echo "  • Julia Field: $OUTPUT_DIR/fields/Julia/"
echo "  • Jack Field: $OUTPUT_DIR/fields/Jack/"
echo "  • St. Malo Field: $OUTPUT_DIR/fields/St. Malo/"
echo ""
echo -e "${BLUE}View main report:${NC}"
echo "  file://$OUTPUT_DIR/npv_analysis/index.html"
