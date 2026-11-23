#!/bin/bash
# ABOUTME: Master script to refresh all BSEE data sources
# ABOUTME: Orchestrates downloads from data.bsee.gov for production, WAR, APD, etc.

set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

# Script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
DATA_DIR="$PROJECT_ROOT/data/modules/bsee"
LOG_DIR="$PROJECT_ROOT/logs/bsee"
LOG_FILE="$LOG_DIR/refresh_$(date +%Y%m%d_%H%M%S).log"

# Create log directory
mkdir -p "$LOG_DIR"

# Tracking variables
TOTAL_STEPS=0
COMPLETED_STEPS=0
FAILED_STEPS=0

# Function to log messages
log() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"

    case $level in
        INFO)    echo -e "${BLUE}[$level]${NC} $message" ;;
        SUCCESS) echo -e "${GREEN}[$level]${NC} $message" ;;
        WARNING) echo -e "${YELLOW}[$level]${NC} $message" ;;
        ERROR)   echo -e "${RED}[$level]${NC} $message" ;;
    esac
}

# Function to run a refresh step
run_step() {
    local step_name="$1"
    local step_cmd="$2"

    ((TOTAL_STEPS++))

    log "INFO" "Starting: $step_name"
    echo ""

    if eval "$step_cmd" >> "$LOG_FILE" 2>&1; then
        log "SUCCESS" "✓ Completed: $step_name"
        ((COMPLETED_STEPS++))
        return 0
    else
        log "ERROR" "✗ Failed: $step_name"
        ((FAILED_STEPS++))
        return 1
    fi
}

# Print header
echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║              BSEE Data Refresh - Master Script                 ║"
echo "╠════════════════════════════════════════════════════════════════╣"
echo "║  Source: data.bsee.gov                                         ║"
echo "║  Data:   Production, WAR, APD, Well Data                       ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo ""
echo -e "Log file: ${YELLOW}$LOG_FILE${NC}"
echo ""

# Parse arguments
MODULES=()
YEARS=""
VERBOSE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --production|-p)
            MODULES+=("production")
            shift
            ;;
        --war|-w)
            MODULES+=("war")
            shift
            ;;
        --apd|-a)
            MODULES+=("apd")
            shift
            ;;
        --all)
            MODULES=("production" "war" "apd")
            shift
            ;;
        --years|-y)
            shift
            YEARS="--years"
            while [[ $# -gt 0 && ! $1 == -* ]]; do
                YEARS="$YEARS $1"
                shift
            done
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS] [MODULES]"
            echo ""
            echo "Modules:"
            echo "  --production, -p   Refresh OGOR-A production data"
            echo "  --war, -w          Refresh Well Activity Reports"
            echo "  --apd, -a          Refresh Application for Permit to Drill"
            echo "  --all              Refresh all data modules"
            echo ""
            echo "Options:"
            echo "  --years, -y YEAR...  Download specific years"
            echo "  --verbose, -v        Show detailed output"
            echo "  --help, -h           Show this help"
            echo ""
            echo "Examples:"
            echo "  $0 --production               # Refresh production data only"
            echo "  $0 --all                      # Refresh all modules"
            echo "  $0 --production --years 2025  # Refresh 2025 production data"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Default to production if no modules specified
if [[ ${#MODULES[@]} -eq 0 ]]; then
    MODULES=("production")
fi

log "INFO" "Modules to refresh: ${MODULES[*]}"
echo ""

# ============================================================
# REFRESH MODULES
# ============================================================

for module in "${MODULES[@]}"; do
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    case $module in
        production)
            echo -e "${CYAN}Refreshing OGOR-A Production Data${NC}"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

            CMD="$SCRIPT_DIR/refresh_production_data.sh $YEARS"
            if $VERBOSE; then
                run_step "OGOR-A Production Data" "$CMD"
            else
                run_step "OGOR-A Production Data" "$CMD"
            fi
            ;;

        war)
            echo -e "${CYAN}Refreshing Well Activity Reports (WAR)${NC}"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

            # WAR refresh script (placeholder - create if needed)
            if [[ -f "$SCRIPT_DIR/refresh_war_data.sh" ]]; then
                run_step "Well Activity Reports" "$SCRIPT_DIR/refresh_war_data.sh"
            else
                log "WARNING" "WAR refresh script not found: $SCRIPT_DIR/refresh_war_data.sh"
                log "INFO" "Skipping WAR refresh"
            fi
            ;;

        apd)
            echo -e "${CYAN}Refreshing Application for Permit to Drill (APD)${NC}"
            echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

            # APD refresh script (placeholder - create if needed)
            if [[ -f "$SCRIPT_DIR/refresh_apd_data.sh" ]]; then
                run_step "Application for Permit to Drill" "$SCRIPT_DIR/refresh_apd_data.sh"
            else
                log "WARNING" "APD refresh script not found: $SCRIPT_DIR/refresh_apd_data.sh"
                log "INFO" "Skipping APD refresh"
            fi
            ;;

        *)
            log "WARNING" "Unknown module: $module"
            ;;
    esac

    echo ""
done

# ============================================================
# SUMMARY
# ============================================================

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                    REFRESH SUMMARY                             ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "Total steps:     ${BLUE}$TOTAL_STEPS${NC}"
echo -e "Completed:       ${GREEN}$COMPLETED_STEPS${NC}"
echo -e "Failed:          ${RED}$FAILED_STEPS${NC}"
echo ""
echo -e "Log file: ${YELLOW}$LOG_FILE${NC}"
echo ""

# Show current data status
echo -e "${BLUE}Current BSEE Production Data:${NC}"
ls -lh "$DATA_DIR/zip/historical_production_yearly"/ogora202*.zip 2>/dev/null | \
    awk '{print "  " $9 " (" $5 ", " $6 " " $7 " " $8 ")"}'

echo ""

# Exit with appropriate code
if [[ $FAILED_STEPS -gt 0 ]]; then
    echo -e "${RED}Some steps failed. Check log for details.${NC}"
    exit 1
else
    echo -e "${GREEN}All steps completed successfully!${NC}"
    exit 0
fi
