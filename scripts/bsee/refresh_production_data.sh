#!/bin/bash
# ABOUTME: Refresh BSEE OGOR-A production data from data.bsee.gov
# ABOUTME: Downloads yearly production data using browser automation

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/refresh_production_data.py"
OUTPUT_DIR="$PROJECT_ROOT/data/modules/bsee/zip/historical_production_yearly"

# Print header
echo -e "${BLUE}========================================"
echo -e "BSEE Production Data Refresh"
echo -e "========================================${NC}"
echo ""
echo -e "Source: ${YELLOW}https://www.data.bsee.gov/Main/OGOR-A.aspx${NC}"
echo -e "Output: ${YELLOW}$OUTPUT_DIR${NC}"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 not found${NC}"
    exit 1
fi

# Check if playwright is installed
if ! python3 -c "import playwright" 2>/dev/null; then
    echo -e "${YELLOW}Installing playwright...${NC}"
    pip install playwright -q
    python3 -m playwright install chromium
fi

# Parse arguments
YEARS=""
ALL_YEARS=""
LIST_ONLY=""
FILE_TYPE="delimit"

while [[ $# -gt 0 ]]; do
    case $1 in
        --years|-y)
            shift
            YEARS="--years"
            while [[ $# -gt 0 && ! $1 == -* ]]; do
                YEARS="$YEARS $1"
                shift
            done
            ;;
        --all|-a)
            ALL_YEARS="--all"
            shift
            ;;
        --list|-l)
            LIST_ONLY="--list"
            shift
            ;;
        --type|-t)
            FILE_TYPE="$2"
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --years, -y YEAR...   Download specific years"
            echo "  --all, -a             Download all available years"
            echo "  --list, -l            List available files only"
            echo "  --type, -t TYPE       File type: delimit (default) or fixed"
            echo "  --help, -h            Show this help"
            echo ""
            echo "Examples:"
            echo "  $0                    # Download current + previous year"
            echo "  $0 --years 2024 2025  # Download specific years"
            echo "  $0 --all              # Download all years (1996-current)"
            echo "  $0 --list             # List available files"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Build command
CMD="python3 $PYTHON_SCRIPT --output $OUTPUT_DIR --type $FILE_TYPE"

if [[ -n "$YEARS" ]]; then
    CMD="$CMD $YEARS"
elif [[ -n "$ALL_YEARS" ]]; then
    CMD="$CMD $ALL_YEARS"
fi

if [[ -n "$LIST_ONLY" ]]; then
    CMD="$CMD $LIST_ONLY"
fi

# Execute
echo -e "${BLUE}Executing: $CMD${NC}"
echo ""

eval $CMD
EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo -e "${GREEN}========================================"
    echo -e "Refresh Complete!"
    echo -e "========================================${NC}"

    # Show updated files
    echo ""
    echo -e "${BLUE}Updated files:${NC}"
    ls -lh "$OUTPUT_DIR"/ogora202*.zip 2>/dev/null | tail -5
else
    echo -e "${RED}========================================"
    echo -e "Refresh Failed"
    echo -e "========================================${NC}"
fi

exit $EXIT_CODE
