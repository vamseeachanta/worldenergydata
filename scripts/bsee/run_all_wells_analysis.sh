#!/bin/bash
# ABOUTME: Execute comprehensive BSEE well analysis across all wells
# ABOUTME: Processes production data, directional surveys, and completion data for all BSEE wells

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUTPUT_DIR="${1:-$PROJECT_ROOT/reports/bsee/all_wells}"
CONFIG_FILE="${2:-$PROJECT_ROOT/config/input/bsee_all_wells.yaml}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}BSEE All Wells Analysis${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo -e "${RED}Error: Python not found${NC}"
    echo "Please ensure Python 3.9+ is installed"
    exit 1
fi

# Create output directory
mkdir -p "$OUTPUT_DIR"
echo -e "${GREEN}✓ Output directory: $OUTPUT_DIR${NC}"
echo ""

# Run production data analysis
echo -e "${YELLOW}Step 1: Analyzing production data for all wells...${NC}"
python "$PROJECT_ROOT/scripts/analyze_production_by_lease.py" \
    --output "$OUTPUT_DIR/production_analysis" \
    --format html \
    --interactive

echo -e "${GREEN}✓ Production analysis complete${NC}"
echo ""

# Run FDAS enhanced BSEE data analysis
echo -e "${YELLOW}Step 2: Enhancing BSEE data with FDAS information...${NC}"
python "$PROJECT_ROOT/scripts/fdas_enhance_bsee_data.py" \
    --output "$OUTPUT_DIR/fdas_enhanced" \
    --format html

echo -e "${GREEN}✓ FDAS enhancement complete${NC}"
echo ""

# Run production report generation
echo -e "${YELLOW}Step 3: Generating comprehensive production reports...${NC}"
python "$PROJECT_ROOT/scripts/generate_production_report.py" \
    --output "$OUTPUT_DIR/production_reports" \
    --format html \
    --interactive

echo -e "${GREEN}✓ Production reports generated${NC}"
echo ""

# Final summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Analysis Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}Results saved to: $OUTPUT_DIR${NC}"
echo ""
echo "Reports generated:"
echo "  • Production Analysis: $OUTPUT_DIR/production_analysis/"
echo "  • FDAS Enhanced Data: $OUTPUT_DIR/fdas_enhanced/"
echo "  • Production Reports: $OUTPUT_DIR/production_reports/"
echo ""
echo -e "${BLUE}View reports in your browser:${NC}"
echo "  file://$OUTPUT_DIR/production_reports/index.html"
