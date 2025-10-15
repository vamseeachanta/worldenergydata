#!/bin/bash
# WorldEnergyData Repository Cleanup Script
# Purpose: Remove duplicate BSEE backup directories
# Expected Space Savings: ~1.5 GB (72% reduction)

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=================================================="
echo "WorldEnergyData Repository Cleanup Script"
echo "=================================================="
echo ""

# Check if we're in the right directory
if [ ! -d "data/modules/bsee" ]; then
    echo -e "${RED}Error: Must run from repository root directory${NC}"
    exit 1
fi

# Display current data size
echo -e "${YELLOW}Current Data Size:${NC}"
du -sh data/
echo ""

# Show backup directories to be deleted
echo -e "${YELLOW}Duplicate Backup Directories (will be deleted):${NC}"
du -sh data/modules/bsee.backup* 2>/dev/null | sort -h || echo "No backups found"
echo ""

# Verify current BSEE data exists
echo -e "${YELLOW}Verifying current BSEE data integrity...${NC}"
if [ -d "data/modules/bsee/current" ]; then
    file_count=$(find data/modules/bsee/current -type f | wc -l)
    echo -e "${GREEN}✓ Found $file_count files in current BSEE data${NC}"
    ls -lh data/modules/bsee/current/*/ 2>/dev/null | head -20
else
    echo -e "${RED}✗ Warning: data/modules/bsee/current/ not found${NC}"
    exit 1
fi
echo ""

# Ask for confirmation
echo -e "${YELLOW}This will DELETE the following directories:${NC}"
echo "  - data/modules/bsee.backup"
echo "  - data/modules/bsee.backup_20250821_055915"
echo "  - data/modules/bsee.backup_20250821_064214"
echo "  - data/modules/bsee.backup_20250821_064447"
echo ""
echo -e "${RED}Expected space recovery: ~1.5 GB${NC}"
echo ""
read -p "Do you want to proceed with cleanup? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo -e "${YELLOW}Cleanup cancelled.${NC}"
    exit 0
fi

# Create optional backup of legacy data before deletion
read -p "Do you want to create a compressed archive of legacy data before deletion? (yes/no): " backup_legacy

if [ "$backup_legacy" = "yes" ]; then
    echo ""
    echo -e "${YELLOW}Creating compressed archive of legacy data...${NC}"
    timestamp=$(date +%Y%m%d_%H%M%S)
    archive_name="bsee_legacy_archive_${timestamp}.tar.gz"

    if [ -d "data/modules/bsee.backup_20250821_055915/legacy" ]; then
        tar -czf "$archive_name" -C data/modules/bsee.backup_20250821_055915 legacy/
        echo -e "${GREEN}✓ Legacy data archived to: $archive_name${NC}"
        echo -e "${GREEN}  Size: $(du -sh $archive_name | cut -f1)${NC}"
    else
        echo -e "${RED}✗ Legacy directory not found, skipping archive${NC}"
    fi
    echo ""
fi

# Execute cleanup
echo -e "${YELLOW}Executing cleanup...${NC}"
echo ""

# Delete backup directories
for backup_dir in data/modules/bsee.backup*; do
    if [ -d "$backup_dir" ]; then
        echo "Removing: $backup_dir"
        rm -rf "$backup_dir"
        echo -e "${GREEN}✓ Deleted: $backup_dir${NC}"
    fi
done

# Remove empty directories in BSEE
echo ""
echo -e "${YELLOW}Removing empty directories...${NC}"
find data/modules/bsee -type d -empty -delete 2>/dev/null && echo -e "${GREEN}✓ Empty directories removed${NC}" || echo "No empty directories found"

# Update .gitignore to prevent future backup commits
echo ""
echo -e "${YELLOW}Updating .gitignore...${NC}"
if ! grep -q "data/modules/\*.backup\*" .gitignore 2>/dev/null; then
    echo "" >> .gitignore
    echo "# Prevent data backup directories from being committed" >> .gitignore
    echo "data/modules/*.backup*" >> .gitignore
    echo -e "${GREEN}✓ .gitignore updated${NC}"
else
    echo "Already in .gitignore"
fi

# Show results
echo ""
echo "=================================================="
echo -e "${GREEN}Cleanup Complete!${NC}"
echo "=================================================="
echo ""
echo -e "${YELLOW}New Data Size:${NC}"
du -sh data/
echo ""
echo -e "${YELLOW}Remaining BSEE Structure:${NC}"
ls -lh data/modules/bsee/
echo ""

# Verify BSEE data integrity post-cleanup
echo -e "${YELLOW}Post-Cleanup Verification:${NC}"
if [ -d "data/modules/bsee/current" ]; then
    file_count=$(find data/modules/bsee/current -type f | wc -l)
    echo -e "${GREEN}✓ Current BSEE data intact: $file_count files${NC}"
else
    echo -e "${RED}✗ Error: Current BSEE data missing!${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}Next Steps:${NC}"
echo "1. Run tests to verify data loading: uv run pytest tests/"
echo "2. Review changes: git status"
echo "3. Commit cleanup: git add . && git commit -m 'chore: remove duplicate BSEE backups (1.5GB)'"
echo ""
