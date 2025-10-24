# PDF Generation Readiness Checklist

> Created: 2025-10-24
> Purpose: Comprehensive pre-flight checklist for generating PDF versions of marketing brochures
> Status: Ready to execute after user decisions

---

## Prerequisites

### System Requirements

- [ ] **Pandoc installed** (document converter)
  ```bash
  # Check if installed
  which pandoc

  # If not found, install:
  sudo apt-get update
  sudo apt-get install -y pandoc
  ```

- [ ] **LaTeX distribution installed** (for PDF generation)
  ```bash
  # Check if texlive-xetex is installed
  which xelatex

  # If not found, install:
  sudo apt-get install -y texlive-xetex texlive-fonts-recommended texlive-fonts-extra
  ```

- [ ] **Python available** (for generator script)
  ```bash
  # Verify Python 3.x
  python --version
  # or
  python3 --version
  ```

### Content Requirements

- [ ] **All user decisions implemented**
  - Wind Energy brochure decision made and executed
  - Contact email decision made and updated
  - All changes committed to git

- [ ] **Git working tree clean**
  ```bash
  git status
  # Should show: "nothing to commit, working tree clean"
  ```

- [ ] **All markdown brochures present and validated**
  ```bash
  # Count markdown brochures
  ls reports/modules/marketing/marketing_brochure_*.md | wc -l
  # Should match expected count (7 or 8 depending on Wind Energy decision)
  ```

---

## Pre-Generation Validation

### Markdown File Checks

**Verify all brochures exist and are well-formed:**
```bash
cd /mnt/github/workspace-hub/worldenergydata

# Check file existence
for brochure in \
  "bsee_data_integration" \
  "economic_evaluation_npv_analysis" \
  "fdas_field_data_analysis_system" \
  "field-specific_analysis" \
  "marine_safety_incident_analysis" \
  "web_scraping_infrastructure" \
  "well_production_dashboard" \
  "wind_energy_data_integration"; do  # Omit if deleted

  file="reports/modules/marketing/marketing_brochure_${brochure}.md"

  if [ -f "$file" ]; then
    echo "✓ $file exists"

    # Check file size (should be > 1KB)
    size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file")
    if [ "$size" -gt 1000 ]; then
      echo "  ✓ Size: $size bytes (adequate)"
    else
      echo "  ⚠ Size: $size bytes (may be too small)"
    fi

    # Check for required sections
    if grep -q "## Overview" "$file" && \
       grep -q "### Key Capabilities" "$file" && \
       grep -q "## Key Benefits" "$file"; then
      echo "  ✓ Required sections present"
    else
      echo "  ⚠ Missing required sections"
    fi

  else
    echo "✗ $file missing"
  fi
  echo ""
done
```

### Content Consistency Checks

**Verify contact information is consistent:**
```bash
# Extract all email addresses from brochures
grep -h "Email:" reports/modules/marketing/marketing_brochure_*.md | sort -u

# Should show only ONE email address
# Expected: Either vamsee.achanta@aceengineer.com OR achantav@gmail.com
```

**Verify repository statistics are present:**
```bash
# Check that all brochures include repository statistics
grep -l "years of development" reports/modules/marketing/marketing_brochure_*.md | wc -l

# Should equal total brochure count
```

**Verify "About WorldEnergyData" section exists:**
```bash
# All brochures should have this section
grep -l "About WorldEnergyData" reports/modules/marketing/marketing_brochure_*.md | wc -l

# Should equal total brochure count
```

---

## PDF Generation

### Test Generation (Single File)

**Before generating all PDFs, test with one brochure:**
```bash
cd /mnt/github/workspace-hub/worldenergydata

# Test with BSEE brochure (usually most complete)
input_file="reports/modules/marketing/marketing_brochure_bsee_data_integration.md"
output_file="reports/modules/marketing/test_brochure.pdf"

# Generate test PDF
pandoc "$input_file" \
  -o "$output_file" \
  --pdf-engine=xelatex \
  -V geometry:margin=1in \
  -V fontsize=11pt \
  -V documentclass=article

# Check if PDF was created
if [ -f "$output_file" ]; then
  echo "✓ Test PDF generation successful"
  ls -lh "$output_file"

  # Open for review (optional)
  # xdg-open "$output_file" 2>/dev/null || open "$output_file" 2>/dev/null
else
  echo "✗ Test PDF generation failed"
fi
```

### Full Generation (All Brochures)

**Method 1: Using generator script (recommended)**
```bash
cd /mnt/github/workspace-hub/worldenergydata

# Generate PDFs for all brochures
python scripts/generate_marketing_brochures.py --pdf

# Check for errors
echo "Exit code: $?"
# 0 = success, non-zero = error

# Verify PDFs were created
ls -lh reports/modules/marketing/*.pdf

# Count PDFs
pdf_count=$(ls reports/modules/marketing/marketing_brochure_*.pdf 2>/dev/null | wc -l)
md_count=$(ls reports/modules/marketing/marketing_brochure_*.md 2>/dev/null | wc -l)

echo "Markdown files: $md_count"
echo "PDF files: $pdf_count"

if [ "$pdf_count" -eq "$md_count" ]; then
  echo "✓ All brochures converted to PDF"
else
  echo "⚠ PDF count ($pdf_count) doesn't match markdown count ($md_count)"
fi
```

**Method 2: Manual batch generation (if script fails)**
```bash
cd /mnt/github/workspace-hub/worldenergydata/reports/modules/marketing

# Loop through all markdown brochures
for md_file in marketing_brochure_*.md; do
  pdf_file="${md_file%.md}.pdf"

  echo "Generating: $pdf_file"

  pandoc "$md_file" \
    -o "$pdf_file" \
    --pdf-engine=xelatex \
    -V geometry:margin=1in \
    -V fontsize=11pt \
    -V documentclass=article

  if [ -f "$pdf_file" ]; then
    echo "  ✓ Success"
  else
    echo "  ✗ Failed"
  fi
done

# Return to repo root
cd ../../..
```

---

## Post-Generation Validation

### File Verification

**Check PDF file properties:**
```bash
cd /mnt/github/workspace-hub/worldenergydata/reports/modules/marketing

for pdf in marketing_brochure_*.pdf; do
  echo "File: $pdf"

  # Check size (PDFs should be 50KB - 500KB typically)
  size=$(stat -f%z "$pdf" 2>/dev/null || stat -c%s "$pdf")
  size_kb=$((size / 1024))
  echo "  Size: ${size_kb}KB"

  if [ "$size_kb" -lt 10 ]; then
    echo "  ⚠ File may be too small (possible generation error)"
  elif [ "$size_kb" -gt 1000 ]; then
    echo "  ⚠ File is very large (check for issues)"
  else
    echo "  ✓ File size looks reasonable"
  fi

  # Check if file is a valid PDF
  if file "$pdf" | grep -q "PDF"; then
    echo "  ✓ Valid PDF format"
  else
    echo "  ✗ Not a valid PDF file"
  fi

  echo ""
done

cd ../../..
```

### Visual Review Checklist

**Manually review each PDF for:**

- [ ] **Formatting**
  - Headers render correctly
  - Bullet points display properly
  - Line breaks are appropriate
  - No text overflow or truncation

- [ ] **Typography**
  - Font sizes are readable (11pt body text)
  - Section headers are clearly distinguished
  - Bold/italic formatting preserved from markdown

- [ ] **Layout**
  - Margins are consistent (1 inch on all sides)
  - Page breaks are logical (don't split sections awkwardly)
  - Two-page structure maintained (or appropriate pagination)

- [ ] **Content Accuracy**
  - All sections from markdown are present
  - Contact information correct
  - Repository statistics accurate
  - No missing images or charts (if applicable)

- [ ] **Special Characters**
  - Bullets (•) render correctly
  - Arrows (→) display properly
  - Checkmarks (✓) if present
  - Any technical symbols preserved

### Automated Content Verification

**Extract text from PDFs and compare with markdown:**
```bash
# Requires pdftotext (from poppler-utils)
# sudo apt-get install poppler-utils

cd reports/modules/marketing

for md_file in marketing_brochure_*.md; do
  pdf_file="${md_file%.md}.pdf"
  txt_file="${md_file%.md}.txt"

  if [ -f "$pdf_file" ]; then
    echo "Extracting text from: $pdf_file"

    # Extract text
    pdftotext "$pdf_file" "$txt_file"

    # Check word count comparison
    md_words=$(wc -w < "$md_file")
    txt_words=$(wc -w < "$txt_file")

    echo "  Markdown: $md_words words"
    echo "  PDF: $txt_words words"

    # PDFs typically have slightly fewer words due to formatting
    # Should be within 10% of markdown
    diff_pct=$(( (md_words - txt_words) * 100 / md_words ))

    if [ "$diff_pct" -lt 15 ]; then
      echo "  ✓ Word count reasonable (${diff_pct}% difference)"
    else
      echo "  ⚠ Significant word count difference (${diff_pct}%)"
    fi

    # Clean up temporary text file
    rm "$txt_file"
  fi
  echo ""
done

cd ../../..
```

---

## Distribution Preparation

### File Organization

**Organize PDFs for distribution:**
```bash
cd /mnt/github/workspace-hub/worldenergydata

# Create distribution directory (optional)
mkdir -p reports/modules/marketing/pdf_distribution

# Copy all PDFs to distribution folder
cp reports/modules/marketing/marketing_brochure_*.pdf \
   reports/modules/marketing/pdf_distribution/

# Create a README for the PDF folder
cat > reports/modules/marketing/pdf_distribution/README.txt << 'EOF'
WorldEnergyData Marketing Brochures - PDF Collection
=====================================================

Generated: $(date)

This folder contains professional marketing brochures for WorldEnergyData modules.

Files:
------
- marketing_brochure_bsee_data_integration.pdf
- marketing_brochure_economic_evaluation_npv_analysis.pdf
- marketing_brochure_fdas_field_data_analysis_system.pdf
- marketing_brochure_field-specific_analysis.pdf
- marketing_brochure_marine_safety_incident_analysis.pdf
- marketing_brochure_web_scraping_infrastructure.pdf
- marketing_brochure_well_production_dashboard.pdf
[- marketing_brochure_wind_energy_data_integration.pdf]  # If applicable

Contact:
--------
Email: [vamsee.achanta@aceengineer.com OR achantav@gmail.com]
GitHub: github.com/vamseeachanta/worldenergydata

For more information, visit the repository or contact us via email.
EOF

# List distribution files
ls -lh reports/modules/marketing/pdf_distribution/
```

### Git Tracking Decision

**Decide whether to commit PDFs to git:**

**Option 1: Commit PDFs (recommended for small repos)**
```bash
# PDFs are typically 50-200KB each
# Total: ~400KB - 1.6MB for 8 brochures
# Reasonable for git tracking

git add reports/modules/marketing/*.pdf

git commit -m "Add PDF versions of marketing brochures

- Generated PDFs from all markdown brochures
- Used pandoc with xelatex engine
- 1-inch margins, 11pt font, article documentclass
- Ready for distribution

Total PDFs: $(ls reports/modules/marketing/*.pdf | wc -l)
Total size: $(du -sh reports/modules/marketing/*.pdf | tail -1 | cut -f1)

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push
```

**Option 2: Exclude PDFs from git (better for large files)**
```bash
# Add to .gitignore
echo "*.pdf" >> .gitignore
echo "# Exclude generated PDFs (regenerate with --pdf flag)" >> .gitignore

git add .gitignore
git commit -m "Exclude PDFs from git tracking

PDFs can be regenerated with:
  python scripts/generate_marketing_brochures.py --pdf

Reduces repository size and avoids binary file tracking.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push

# Note: PDFs remain in working directory but not tracked
```

---

## Troubleshooting

### Common Issues and Fixes

**Issue 1: Pandoc not found**
```bash
# Error: command not found: pandoc
# Solution:
sudo apt-get update
sudo apt-get install -y pandoc texlive-xetex
```

**Issue 2: LaTeX engine errors**
```bash
# Error: xelatex not found
# Solution:
sudo apt-get install -y texlive-xetex texlive-fonts-recommended texlive-fonts-extra
```

**Issue 3: Unicode/special character errors**
```bash
# Error: Cannot encode character
# Solution: Use xelatex instead of pdflatex
pandoc input.md -o output.pdf --pdf-engine=xelatex
```

**Issue 4: PDFs are blank or incomplete**
```bash
# Check markdown file is valid
cat reports/modules/marketing/marketing_brochure_bsee_data_integration.md

# Try regenerating with verbose output
pandoc input.md -o output.pdf --pdf-engine=xelatex --verbose

# Check pandoc version
pandoc --version
# Should be 2.x or higher
```

**Issue 5: Formatting issues in PDFs**
```bash
# Try different document class
pandoc input.md -o output.pdf --pdf-engine=xelatex -V documentclass=report

# Adjust margins
pandoc input.md -o output.pdf --pdf-engine=xelatex -V geometry:margin=0.75in

# Change font size
pandoc input.md -o output.pdf --pdf-engine=xelatex -V fontsize=10pt
```

---

## Final Checklist

Before declaring PDFs ready for distribution:

- [ ] All user decisions implemented (Wind Energy, contact email)
- [ ] All markdown brochures validated
- [ ] Pandoc and LaTeX installed
- [ ] Test PDF generation successful
- [ ] All brochures converted to PDF
- [ ] PDF count matches markdown count
- [ ] All PDFs are valid (file command confirms)
- [ ] PDF file sizes are reasonable (50-500KB each)
- [ ] Visual review completed for all PDFs
- [ ] Formatting is correct (headers, bullets, spacing)
- [ ] Contact information is accurate in all PDFs
- [ ] Repository statistics are current
- [ ] Git tracking decision made (commit PDFs or exclude)
- [ ] PDFs organized for distribution (if needed)
- [ ] README created for PDF distribution folder (if applicable)

---

## Distribution Channels

Once PDFs are ready:

### Email Distribution
```bash
# Attach PDFs to email
# Recipients: stakeholders, team members, clients
# Subject: "WorldEnergyData Marketing Brochures - [Module Name]"
```

### Website Upload
- Upload to company website's /resources/ or /brochures/ section
- Create landing page linking to all PDF brochures
- Add download tracking analytics (optional)

### GitHub Release
```bash
# Create GitHub release with PDFs as assets
gh release create v1.0-marketing \
  reports/modules/marketing/*.pdf \
  --title "Marketing Brochures v1.0" \
  --notes "Professional marketing brochures for all WorldEnergyData modules"
```

### Social Media
- LinkedIn: Post individual brochures with summaries
- Twitter: Share links to PDF downloads
- Industry forums: Distribute relevant brochures

---

## Maintenance

### Updating PDFs

**When markdown brochures are updated:**
```bash
cd /mnt/github/workspace-hub/worldenergydata

# Regenerate all PDFs
python scripts/generate_marketing_brochures.py --pdf

# Or regenerate specific brochure
pandoc reports/modules/marketing/marketing_brochure_[name].md \
  -o reports/modules/marketing/marketing_brochure_[name].pdf \
  --pdf-engine=xelatex \
  -V geometry:margin=1in

# Commit updated PDFs (if tracked in git)
git add reports/modules/marketing/*.pdf
git commit -m "Update PDF brochures - [describe changes]"
git push
```

### Version Control

**Consider adding version numbers to PDFs:**
- Update YAML config with version field
- Include version in PDF footer
- Maintain changelog of brochure updates

---

**End of PDF Generation Readiness Checklist**

> All prerequisites and procedures documented.
> Ready to execute after user decisions are implemented.
