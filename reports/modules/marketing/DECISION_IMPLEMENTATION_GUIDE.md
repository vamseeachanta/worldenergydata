# Decision Implementation Guide

> Created: 2025-10-24
> Purpose: Ready-to-execute procedures for implementing user decisions on Wind Energy brochure and contact email
> Status: Awaiting user decisions

---

## Executive Summary

This guide provides complete, ready-to-execute procedures for implementing decisions identified in VALIDATION_REPORT.md. All commands and file modifications are prepared for immediate execution once decisions are made.

---

## Decision 1: Wind Energy Data Integration Brochure

**Issue**: Brochure generated for non-existent module at `src/worldenergydata/modules/wind`

**Current File**: `reports/modules/marketing/marketing_brochure_wind_energy_data_integration.md`

### Option A: Delete Brochure (RECOMMENDED)

**Rationale**: Ensures 100% accuracy in marketing materials, prevents misleading potential users

**Files to Modify**:
1. Delete brochure file
2. Update GENERATION_SUMMARY.md (change 8 to 7 brochures)
3. Update QUICK_START.md (remove from Tier 1 list)
4. Update VALIDATION_REPORT.md (mark as removed)
5. Update worldenergydata_marketing_config.yaml (mark as tier_4_optional or remove)

**Execution Commands**:
```bash
# 1. Delete the Wind Energy brochure
rm reports/modules/marketing/marketing_brochure_wind_energy_data_integration.md

# 2. Update GENERATION_SUMMARY.md (manual edit required)
# Change line 11: "### ✅ Tier 1: Core Modules (3 brochures)" to "(2 brochures)"
# Remove Wind Energy section (lines 25-30)
# Update summary statistics to show 7 brochures instead of 8

# 3. Update QUICK_START.md (manual edit required)
# Change line 5: "All 8 brochures are already generated!" to "All 7 brochures..."
# Remove line 12: "- [Wind Energy Data Integration](marketing_brochure_wind_energy_data_integration.md)"

# 4. Commit changes
git add -A
git commit -m "Remove Wind Energy brochure - module not yet implemented

- Deleted marketing_brochure_wind_energy_data_integration.md
- Updated GENERATION_SUMMARY.md to reflect 7 brochures
- Updated QUICK_START.md to remove Wind Energy from list
- Ensures 100% accuracy of marketing materials

See VALIDATION_REPORT.md for rationale.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# 5. Push to remote
git push
```

**Expected Result**: 7 accurate brochures (87.5% → 100% accuracy rate after removing inaccurate one)

---

### Option B: Mark as "Coming Soon"

**Rationale**: Maintains visibility of planned feature while being transparent about current status

**Files to Modify**:
1. Update brochure with "Coming Soon" banner
2. Update VALIDATION_REPORT.md (mark as "Coming Soon" status)
3. Add disclaimer to brochure about planned implementation

**Execution Procedure**:

**Step 1**: Update `marketing_brochure_wind_energy_data_integration.md`
```markdown
# Wind Energy Data Integration
## Renewable energy data collection and analysis system

> **⚠️ COMING SOON**: This module is currently under development and not yet available.
> Expected release: [USER TO SPECIFY DATE]

### Overview

[Keep existing overview text, but add disclaimer...]

**Note**: This brochure describes planned capabilities. The Wind Energy module is currently in development and not available in the current release. For information about available modules, see BSEE Data Integration, Marine Safety Incident Analysis, or other completed modules listed in QUICK_START.md.
```

**Step 2**: Update GENERATION_SUMMARY.md
```markdown
3. **Wind Energy Data Integration** ⚠️ COMING SOON
   - File: `marketing_brochure_wind_energy_data_integration.md`
   - Size: 3.0 KB
   - Focus: Planned renewable energy data collection for wind sector
   - **Status**: Module in development, brochure describes planned capabilities
```

**Step 3**: Commit changes
```bash
git add reports/modules/marketing/marketing_brochure_wind_energy_data_integration.md \
        reports/modules/marketing/GENERATION_SUMMARY.md

git commit -m "Mark Wind Energy brochure as 'Coming Soon'

- Added prominent disclaimer to Wind Energy brochure
- Updated GENERATION_SUMMARY.md to note module status
- Maintains transparency about planned vs. available features
- Brochure describes future capabilities, not current implementation

See VALIDATION_REPORT.md for background.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

---

### Option C: Prioritize Wind Module Implementation

**Rationale**: Deliver on promised capability, align code with marketing materials

**Implementation Scope**: This requires significant development work beyond simple file updates.

**High-Level Steps**:
1. Create module directory structure: `src/worldenergydata/modules/wind/`
2. Implement wind data collection from public databases
3. Add performance benchmarking capabilities
4. Implement cross-sector comparison with oil & gas
5. Create tests (unit, integration)
6. Update documentation

**Directory Structure to Create**:
```
src/worldenergydata/modules/wind/
├── __init__.py
├── data/
│   ├── __init__.py
│   ├── collectors.py        # Wind database data collection
│   ├── processors.py        # Wind data processing
│   └── validators.py        # Data quality validation
├── analysis/
│   ├── __init__.py
│   ├── performance.py       # Performance benchmarking
│   └── comparison.py        # Cross-sector comparison
└── reports/
    ├── __init__.py
    └── generators.py        # Report generation

tests/modules/wind/
├── __init__.py
├── test_collectors.py
├── test_processors.py
├── test_performance.py
└── test_comparison.py
```

**Estimated Effort**: 2-3 weeks of development work

**This option requires user confirmation and detailed requirements gathering before implementation.**

---

## Decision 2: Contact Email Address

**Issue**: Discrepancy between brochure email (vamsee.achanta@aceengineer.com) and git config (achantav@gmail.com)

**Current Email in Brochures**: vamsee.achanta@aceengineer.com
**Git Config Email**: achantav@gmail.com

### Option A: Keep aceengineer.com (No Action Required)

**If you confirm**: "The aceengineer.com email is correct for marketing materials"

**Action**: None - brochures already use this email

**Verification Only**:
```bash
# Just verify all brochures have consistent email
grep -r "vamsee.achanta@aceengineer.com" reports/modules/marketing/*.md

# Expected result: All 8 brochures show this email
```

---

### Option B: Change to gmail.com

**If you confirm**: "Please update all brochures to use achantav@gmail.com"

**Files to Update**: All 8 brochure files + GENERATION_SUMMARY.md

**Execution Commands**:
```bash
# Update all brochure files (using sed for batch replacement)
cd reports/modules/marketing/

# Backup files first (safety)
for file in marketing_brochure_*.md; do
    cp "$file" "$file.backup"
done

# Replace email in all brochures
sed -i 's/vamsee.achanta@aceengineer.com/achantav@gmail.com/g' marketing_brochure_*.md

# Update GENERATION_SUMMARY.md
sed -i 's/vamsee.achanta@aceengineer.com/achantav@gmail.com/g' GENERATION_SUMMARY.md

# Update QUICK_START.md
sed -i 's/vamsee.achanta@aceengineer.com/achantav@gmail.com/g' QUICK_START.md

# Verify replacements
echo "Verifying email updates..."
grep -l "achantav@gmail.com" *.md | wc -l  # Should show 10 files

# Return to repo root
cd ../../..

# Commit changes
git add reports/modules/marketing/*.md

git commit -m "Update contact email across all marketing brochures

- Changed from vamsee.achanta@aceengineer.com to achantav@gmail.com
- Updated all 8 brochures for consistency
- Updated GENERATION_SUMMARY.md and QUICK_START.md
- Aligns with git config user email

See VALIDATION_REPORT.md for rationale.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to remote
git push

# Clean up backups after successful push
rm reports/modules/marketing/*.backup
```

**Verification**:
```bash
# After update, verify no aceengineer.com references remain
grep -r "aceengineer.com" reports/modules/marketing/*.md
# Expected: No results

# Verify gmail.com is present in all brochures
grep -r "achantav@gmail.com" reports/modules/marketing/*.md | wc -l
# Expected: 10 results (8 brochures + GENERATION_SUMMARY + QUICK_START)
```

---

## Combined Decision Scenarios

### Scenario 1: Delete Wind + Keep aceengineer.com
```bash
# Execute Option A for Wind Energy (deletion)
# No action for email (already correct)

# Result: 7 brochures, all with aceengineer.com email, 100% accuracy
```

### Scenario 2: Delete Wind + Change to gmail.com
```bash
# First: Execute Option A for Wind Energy (deletion)
rm reports/modules/marketing/marketing_brochure_wind_energy_data_integration.md

# Second: Execute Option B for email (update to gmail.com)
cd reports/modules/marketing/
sed -i 's/vamsee.achanta@aceengineer.com/achantav@gmail.com/g' marketing_brochure_*.md
sed -i 's/vamsee.achanta@aceengineer.com/achantav@gmail.com/g' GENERATION_SUMMARY.md
sed -i 's/vamsee.achanta@aceengineer.com/achantav@gmail.com/g' QUICK_START.md
cd ../../..

# Single commit for both changes
git add -A
git commit -m "Remove Wind Energy brochure and update contact email

Wind Energy Changes:
- Deleted marketing_brochure_wind_energy_data_integration.md
- Module not yet implemented (see VALIDATION_REPORT.md)
- Updated GENERATION_SUMMARY.md to reflect 7 brochures

Email Changes:
- Changed from vamsee.achanta@aceengineer.com to achantav@gmail.com
- Updated all 7 remaining brochures for consistency
- Aligns with git config user email

Result: 7 accurate brochures with correct contact information

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

### Scenario 3: "Coming Soon" + Keep aceengineer.com
```bash
# Execute Option B for Wind Energy (mark as coming soon)
# No action for email (already correct)

# Result: 8 brochures (1 marked "Coming Soon"), all with aceengineer.com email
```

### Scenario 4: "Coming Soon" + Change to gmail.com
```bash
# First: Update Wind Energy brochure with "Coming Soon" banner
# Second: Update all brochures to gmail.com

# Combined commit showing both changes
```

---

## Post-Decision Tasks

Once decisions are implemented, proceed with:

### 1. Final Brochure Review
```bash
# Review all remaining brochures
for file in reports/modules/marketing/marketing_brochure_*.md; do
    echo "Reviewing: $file"
    head -20 "$file"
    echo "---"
done
```

### 2. PDF Generation (Optional)

**Prerequisites**:
```bash
# Check if pandoc is installed
which pandoc
# If not found, install:
sudo apt-get update
sudo apt-get install -y pandoc texlive-xetex
```

**Generate PDFs**:
```bash
# Navigate to repo root
cd /mnt/github/workspace-hub/worldenergydata

# Generate PDFs for all brochures
python scripts/reporting/generate_marketing_brochures.py --pdf

# PDFs will be created in reports/modules/marketing/ directory
# Expected files: marketing_brochure_*.pdf (one per .md file)
```

**Verify PDFs**:
```bash
# List generated PDFs
ls -lh reports/modules/marketing/*.pdf

# Check PDF count matches markdown count
markdown_count=$(ls reports/modules/marketing/marketing_brochure_*.md | wc -l)
pdf_count=$(ls reports/modules/marketing/marketing_brochure_*.pdf 2>/dev/null | wc -l)

echo "Markdown brochures: $markdown_count"
echo "PDF brochures: $pdf_count"
```

### 3. Distribution Readiness Checklist

- [ ] All decisions implemented and committed
- [ ] Git working tree clean
- [ ] All brochures reviewed for accuracy
- [ ] Contact email verified in all files
- [ ] PDFs generated (if required)
- [ ] PDF formatting reviewed
- [ ] Brochures ready for external distribution

---

## Quick Reference Commands

### Check Current Status
```bash
# How many brochures exist?
ls reports/modules/marketing/marketing_brochure_*.md | wc -l

# What email is currently in brochures?
grep -h "Email:" reports/modules/marketing/marketing_brochure_*.md | sort -u

# Git status
git status

# Working tree clean?
git diff --quiet && echo "Clean" || echo "Uncommitted changes"
```

### Rollback (If Needed)
```bash
# If you need to undo changes before committing:
git restore reports/modules/marketing/*.md

# If you need to undo after committing but before pushing:
git reset --soft HEAD~1

# If you need to undo after pushing (creates new commit):
git revert HEAD
git push
```

---

## User Decision Template

**For easy copy-paste response:**

```
Wind Energy Decision: [Option A / Option B / Option C]
Contact Email Decision: [Keep aceengineer.com / Change to gmail.com]

Additional notes: [Any specific instructions or modifications]
```

---

## Implementation Notes

- All commands are designed for immediate execution
- Sed commands use `-i` flag for in-place editing
- Backups are created before batch replacements
- Git commits include detailed messages explaining rationale
- All changes are reversible before pushing

---

**End of Decision Implementation Guide**

> Awaiting user decisions to proceed with implementation.
> All procedures are ready for immediate execution.
