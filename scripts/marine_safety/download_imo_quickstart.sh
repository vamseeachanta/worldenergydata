#!/bin/bash
# Quick start script for IMO GISIS data download

echo "=========================================="
echo "IMO GISIS Data Downloader - Quick Start"
echo "=========================================="
echo ""

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is not installed"
    echo "   Install with: sudo apt install python3"
    exit 1
fi

echo "✅ Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo "❌ Error: pip3 is not installed"
    echo "   Install with: sudo apt install python3-pip"
    exit 1
fi

echo "✅ pip3 found"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
pip3 install -r scripts/requirements_imo_download.txt

if [ $? -ne 0 ]; then
    echo "❌ Failed to install Python dependencies"
    exit 1
fi

echo "✅ Python dependencies installed"

# Check for Chrome/Chromium
echo ""
echo "🔍 Checking for Chrome/Chromium..."

if command -v google-chrome &> /dev/null; then
    echo "✅ Google Chrome found: $(google-chrome --version)"
elif command -v chromium-browser &> /dev/null; then
    echo "✅ Chromium found: $(chromium-browser --version)"
elif command -v chromium &> /dev/null; then
    echo "✅ Chromium found: $(chromium --version)"
else
    echo "⚠️  Chrome/Chromium not found"
    echo ""
    echo "Install Chrome/Chromium:"
    echo "  Ubuntu/Debian: sudo apt install chromium-browser chromium-chromedriver"
    echo "  Or download Chrome: https://www.google.com/chrome/"
    echo ""
    read -p "Do you want to try installing Chromium now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sudo apt update
        sudo apt install -y chromium-browser chromium-chromedriver
    else
        echo "Please install Chrome/Chromium manually and run this script again"
        exit 1
    fi
fi

# Check for chromedriver
if command -v chromedriver &> /dev/null; then
    echo "✅ chromedriver found: $(chromedriver --version 2>&1 | head -1)"
else
    echo "⚠️  chromedriver not found"
    echo "   Install with: sudo apt install chromium-chromedriver"
fi

# Check for credentials
echo ""
echo "🔐 Checking IMO credentials..."

if [ -z "$IMO_USERNAME" ]; then
    echo "⚠️  IMO_USERNAME environment variable not set"
    read -p "Enter your IMO username/email: " IMO_USERNAME
    export IMO_USERNAME
fi

if [ -z "$IMO_PASSWORD" ]; then
    echo "⚠️  IMO_PASSWORD environment variable not set"
    read -sp "Enter your IMO password: " IMO_PASSWORD
    export IMO_PASSWORD
    echo ""
fi

echo "✅ Credentials configured"

# Ask for year range
echo ""
echo "📅 Date range configuration"
read -p "Start year (default: 2000): " START_YEAR
START_YEAR=${START_YEAR:-2000}

read -p "End year (default: $(date +%Y)): " END_YEAR
END_YEAR=${END_YEAR:-$(date +%Y)}

# Ask for visible mode
echo ""
read -p "Run browser in visible mode for debugging? (y/n, default: n): " -n 1 -r
echo ""
VISIBLE_FLAG=""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    VISIBLE_FLAG="--visible"
fi

# Confirm before proceeding
echo ""
echo "=========================================="
echo "Ready to download IMO GISIS data"
echo "=========================================="
echo "Username: $IMO_USERNAME"
echo "Year range: $START_YEAR - $END_YEAR"
echo "Browser mode: $([ -z "$VISIBLE_FLAG" ] && echo "headless" || echo "visible")"
echo "Output: data/modules/marine_safety/raw/imo_gisis/"
echo ""
read -p "Proceed with download? (y/n): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Download cancelled"
    exit 0
fi

# Run download
echo ""
echo "🚀 Starting download..."
echo ""

python3 scripts/download_imo_gisis_authenticated.py \
    --username "$IMO_USERNAME" \
    --password "$IMO_PASSWORD" \
    --start-year "$START_YEAR" \
    --end-year "$END_YEAR" \
    $VISIBLE_FLAG

# Check result
if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "✅ Download completed successfully!"
    echo "=========================================="
    echo ""
    echo "Downloaded files are in:"
    echo "  data/modules/marine_safety/raw/imo_gisis/"
    echo ""
    echo "View summary:"
    echo "  cat data/modules/marine_safety/raw/imo_gisis/download_summary.json"
    echo ""
    echo "Count records:"
    echo "  cd data/modules/marine_safety/raw/imo_gisis"
    echo "  for file in imo_casualties_*.csv; do"
    echo "    echo \"\$file: \$(tail -n +2 \"\$file\" | wc -l) records\""
    echo "  done"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "⚠️  Download completed with errors"
    echo "=========================================="
    echo ""
    echo "Check the download summary for details:"
    echo "  cat data/modules/marine_safety/raw/imo_gisis/download_summary.json"
    echo ""
    echo "For troubleshooting, see:"
    echo "  scripts/IMO_DOWNLOAD_GUIDE.md"
    echo ""
fi
