# WorldEnergyData - Quick Start Guide

> **Standalone Execution Framework** - No AI Agent Dependencies
>
> Version: 1.0.0
> Created: 2025-10-22

---

## 🚀 Quick Start (30 seconds)

### Run Everything

```bash
# Execute complete analysis suite
cd /mnt/github/workspace-hub/worldenergydata
./scripts/run_all_analyses.sh
```

**That's it!** The complete analysis suite will run and generate a comprehensive report in `reports/complete_analysis_<timestamp>/`

---

## 📊 What Gets Analyzed

### 1. BSEE Well Analysis
- **All wells** production data analysis
- **Lower Tertiary** deepwater fields (Anchor, Julia, Jack, St. Malo)
- **NPV calculations** with economic modeling
- **FDAS enhancement** with field-level data

### 2. Marine Safety Analysis
- **Comprehensive** incident database analysis
- **6 scenarios:** Foundering, Collision, Fire, Machinery, Grounding, Flooding
- **Multi-source** data (USCG, NOAA, MAIB, TSB)
- **AI classification** (optional)

### 3. Production Analysis
- **FDAS production** data retrieval
- **Historical trends** and forecasting
- **Economic metrics**

---

## ⚡ Run Specific Modules

### BSEE Analysis Only

```bash
# All wells
./scripts/bsee/run_all_wells_analysis.sh

# Lower Tertiary fields only
./scripts/bsee/run_lower_tertiary_analysis.sh
```

### Marine Safety Only

```bash
./scripts/marine_safety/run_all_incident_analysis.sh
```

---

## 📁 Where Are Results?

Default output location:
```
reports/
└── complete_analysis_YYYYMMDD_HHMMSS/
    ├── ANALYSIS_SUMMARY.md           ← Start here!
    ├── bsee/
    │   ├── all_wells/
    │   │   └── production_reports/index.html
    │   └── lower_tertiary/
    │       └── npv_analysis/index.html
    └── marine_safety/
        └── database_analysis/index.html
```

---

## 🎯 Main Dashboards

After running, open these in your browser:

```bash
# Complete summary (recommended)
open reports/complete_analysis_*/ANALYSIS_SUMMARY.md

# BSEE dashboards
open reports/complete_analysis_*/bsee/all_wells/production_reports/index.html
open reports/complete_analysis_*/bsee/lower_tertiary/npv_analysis/index.html

# Marine Safety dashboard
open reports/complete_analysis_*/marine_safety/database_analysis/index.html
```

---

## ⚙️ Custom Output Location

```bash
# Specify where results should go
./scripts/run_all_analyses.sh /path/to/my/results

# Example: Save to desktop
./scripts/run_all_analyses.sh ~/Desktop/energy_analysis
```

---

## 🔧 Prerequisites

### Required
- **Python 3.9+** (detected automatically)
- **Dependencies** (install once):

```bash
# Using UV (recommended, faster)
uv sync

# OR using pip
pip install pandas numpy plotly matplotlib numpy-financial pyyaml
```

### Optional
- **UV package manager** (for faster dependency management)
- **Git** (already present)

---

## ⏱️ How Long Does It Take?

- **Complete suite:** 20-45 minutes (all analyses)
- **BSEE all wells:** 5-15 minutes
- **Lower Tertiary:** 3-8 minutes
- **Marine Safety:** 10-20 minutes

Progress is shown in console with color-coded output.

---

## 📖 Detailed Documentation

- **Scripts README:** `scripts/README.md` - Complete documentation
- **User Requirements:** `user_prompt.md` - Full requirements spec
- **Configuration:** `config/input/*.yaml` - YAML configs for each module
- **Workflow Guide:** `docs/DEVELOPMENT_WORKFLOW.md` - Development process

---

## 🛠️ Troubleshooting

### "Python not found"
```bash
# Install Python 3.9+
# Ubuntu/Debian:
sudo apt install python3.9

# macOS:
brew install python@3.9
```

### "Permission denied"
```bash
# Make scripts executable
chmod +x scripts/*.sh
chmod +x scripts/bsee/*.sh
chmod +x scripts/marine_safety/*.sh
```

### "Module not found"
```bash
# Install dependencies
uv sync
# OR
pip install -r requirements.txt
```

---

## 📊 Interactive Features

All generated reports include:
- ✅ **Plotly visualizations** (hover, zoom, pan)
- ✅ **Interactive tables** (sort, filter)
- ✅ **Export options** (PNG, SVG, CSV)
- ✅ **Responsive design** (mobile-friendly)
- ✅ **No static images** (all interactive)

---

## 🎨 Example Commands

```bash
# Complete analysis
./scripts/run_all_analyses.sh

# BSEE only
./scripts/bsee/run_all_wells_analysis.sh

# Lower Tertiary with custom output
./scripts/bsee/run_lower_tertiary_analysis.sh ~/my_analysis

# Marine Safety with config file
./scripts/marine_safety/run_all_incident_analysis.sh \
    ~/output \
    config/input/marine_safety.yaml

# Custom NPV parameters (via Python directly)
python scripts/analyze_lower_tertiary_npv.py \
    --discount-rate 0.12 \
    --oil-price 85.0 \
    --output ~/custom_npv
```

---

## 🚦 Status Indicators

Scripts use color-coded output:

- 🔵 **Blue** - Section headers, information
- 🟡 **Yellow** - Processing steps, warnings
- 🟢 **Green** - Success, completion
- 🔴 **Red** - Errors (with helpful messages)

---

## 💡 Pro Tips

1. **Run overnight** - Complete suite takes 20-45 minutes
2. **Check ANALYSIS_SUMMARY.md first** - Quick overview of all results
3. **Bookmark dashboards** - Main index.html files for quick access
4. **Export data** - All reports include CSV export options
5. **Custom configs** - Edit YAML files in `config/input/` for customization

---

## 📞 Support

- **Scripts documentation:** `scripts/README.md`
- **Configuration examples:** `config/input/*.yaml`
- **Development workflow:** `docs/DEVELOPMENT_WORKFLOW.md`

---

## ✅ Verification

Test that everything works:

```bash
# 1. Check Python
python --version
# Should show 3.9 or higher

# 2. Check dependencies
python -c "import pandas, numpy, plotly; print('✓ Dependencies OK')"

# 3. Run a quick test (Lower Tertiary only, fastest)
./scripts/bsee/run_lower_tertiary_analysis.sh

# 4. Open the results
open reports/bsee/lower_tertiary/npv_analysis/index.html
```

---

**Ready to analyze energy data! 🚀**

For detailed documentation, see `scripts/README.md`
