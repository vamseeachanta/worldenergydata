#!/bin/bash
# Download IMO GISIS data year by year to avoid timeouts

USERNAME="vamseeachanta"
PASSWORD="rose109@Gudda"

echo "=========================================="
echo "IMO GISIS Year-by-Year Download"
echo "=========================================="
echo ""

# Start from 1990 and go to current year
START_YEAR=1990
END_YEAR=2025

SUCCESS=0
FAILED=0

for YEAR in $(seq $START_YEAR $END_YEAR); do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📅 Year $YEAR"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    # Run download for single year with timeout
    IMO_USERNAME="$USERNAME" IMO_PASSWORD="$PASSWORD" \
        timeout 120 python3 scripts/download_imo_gisis_authenticated.py \
        --start-year $YEAR \
        --end-year $YEAR \
        2>&1 | tee -a /tmp/imo_download_$YEAR.log

    RESULT=$?

    if [ $RESULT -eq 0 ]; then
        echo "✅ Year $YEAR: Success"
        SUCCESS=$((SUCCESS + 1))
    elif [ $RESULT -eq 124 ]; then
        echo "⏱️  Year $YEAR: Timeout (120s exceeded)"
        FAILED=$((FAILED + 1))
    else
        echo "❌ Year $YEAR: Failed (exit code: $RESULT)"
        FAILED=$((FAILED + 1))
    fi

    # Brief pause between years
    sleep 3
    echo ""
done

echo "=========================================="
echo "Download Complete"
echo "=========================================="
echo "✅ Successful: $SUCCESS years"
echo "❌ Failed: $FAILED years"
echo ""
echo "Check downloaded files:"
echo "  ls -lh data/modules/marine_safety/raw/imo_gisis/imo_casualties_*.csv"
echo ""
echo "View summary:"
echo "  cat data/modules/marine_safety/raw/imo_gisis/download_summary.json"
echo ""
