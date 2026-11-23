#!/bin/bash
# Quick test script to verify all bash scripts are executable

echo "Testing WorldEnergyData Bash Scripts"
echo "====================================="
echo ""

# Test each script exists and is executable
SCRIPTS=(
    "run_all_analyses.sh"
    "bsee/run_all_wells_analysis.sh"
    "bsee/run_lower_tertiary_analysis.sh"
    "marine_safety/run_all_incident_analysis.sh"
)

cd "$(dirname "$0")"
ALL_OK=true

for SCRIPT in "${SCRIPTS[@]}"; do
    if [ -f "$SCRIPT" ]; then
        if [ -x "$SCRIPT" ]; then
            echo "✓ $SCRIPT - OK"
        else
            echo "✗ $SCRIPT - Not executable (run: chmod +x $SCRIPT)"
            ALL_OK=false
        fi
    else
        echo "✗ $SCRIPT - Not found"
        ALL_OK=false
    fi
done

echo ""
if [ "$ALL_OK" = true ]; then
    echo "✓ All scripts are ready to execute!"
    echo ""
    echo "Try running:"
    echo "  ./scripts/bsee/run_lower_tertiary_analysis.sh"
else
    echo "✗ Some scripts have issues (see above)"
fi
