# Quick Start Guide: Marketing Brochures

## 🚀 Ready-to-Use Brochures

**All 7 brochures are already generated!** No setup required.

## 📂 Available Brochures

### Tier 1: Core Modules
- [BSEE Data Integration](marketing_brochure_bsee_data_integration.md)
- [Marine Safety Incident Analysis](marketing_brochure_marine_safety_incident_analysis.md)

### Tier 2: Advanced Modules
- [Economic Evaluation (NPV Analysis)](marketing_brochure_economic_evaluation_npv_analysis.md)
- [Field-Specific Analysis](marketing_brochure_field-specific_analysis.md)
- [Well Production Dashboard](marketing_brochure_well_production_dashboard.md)

### Tier 3: Integration Modules
- [Web Scraping Infrastructure](marketing_brochure_web_scraping_infrastructure.md)
- [FDAS (Field Data Analysis System)](marketing_brochure_fdas_field_data_analysis_system.md)

## 🎯 Common Tasks

### View a Brochure
```bash
cat reports/modules/marketing/marketing_brochure_bsee_data_integration.md
```

### Generate PDFs
```bash
# Install pandoc first (one-time setup)
sudo apt-get install pandoc texlive-xetex

# Generate all PDFs
python scripts/generate_marketing_brochures.py --pdf
```

### Regenerate All Brochures
```bash
python scripts/generate_marketing_brochures.py
```

### Regenerate Specific Tier
```bash
# Only Tier 1 (core modules)
python scripts/generate_marketing_brochures.py --tier tier_1_core

# Only Tier 2 (advanced modules)
python scripts/generate_marketing_brochures.py --tier tier_2_advanced

# Only Tier 3 (integration modules)
python scripts/generate_marketing_brochures.py --tier tier_3_integration
```

## ✏️ Customize Brochures

1. **Edit configuration:**
   ```bash
   nano specs/modules/marketing/worldenergydata_marketing_config.yaml
   ```

2. **Update module capabilities, statistics, or descriptions**

3. **Regenerate brochures:**
   ```bash
   python scripts/generate_marketing_brochures.py
   ```

## 📧 Share Brochures

### Via Email
Attach markdown files or PDFs to emails

### On Website
Copy markdown to your documentation site

### In Presentations
Convert to PDF and include in slide decks

### In README
Link to specific brochures from main README

## ❓ Questions?

See [GENERATION_SUMMARY.md](GENERATION_SUMMARY.md) for full details.

Contact: vamsee.achanta@aceengineer.com
