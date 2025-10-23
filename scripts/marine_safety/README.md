# Marine Safety Incident Analysis - Usage Guide

## Quick Start

Run the marine safety incident analysis with a single bash command:

```bash
bash scripts/marine_safety/analyze_incidents.sh
```

This will:
1. Check for LLM dependencies (transformers, torch)
2. Analyze incidents from CSV input files
3. Generate interactive HTML reports
4. Display report locations when complete

## Input Data Files

The analysis requires three CSV input files in `data/modules/marine_safety/input/`:

1. **hatch_incidents.csv** - Hatch and opening maloperation incidents
2. **foundering_incidents.csv** - Vessel foundering events
3. **fatality_incidents.csv** - Fatal incidents aboard vessels

### CSV Format Examples

**hatch_incidents.csv:**
```csv
incident_id,date,vessel_name,description,severity,location
H001,2024-01-15,MV Atlantic Star,"Engine room hatch left open during rough seas...",Critical,"North Atlantic"
```

**foundering_incidents.csv:**
```csv
incident_id,date,vessel_name,description,fatalities,location
F001,2024-01-22,Cargo Ship Atlantis,"Vessel foundered in severe weather...",0,"North Atlantic"
```

**fatality_incidents.csv:**
```csv
incident_id,date,vessel_name,description,fatalities,cause_of_death,location
FA001,2024-01-10,Bulk Carrier Oceanic,"Crew member fell from ladder...",1,"Fall from height","Port of Guangzhou"
```

## Output Reports

The analysis generates four HTML reports in `reports/marine_safety/YYYYMMDD_HHMMSS/`:

1. **executive_summary.html** - Executive summary for supervisor presentation
   - Key metrics and statistics
   - Summary by incident type
   - Recommendations
   - Links to detailed reports

2. **hatch_analysis.html** - Detailed hatch maloperation analysis
   - Interactive visualizations (Plotly)
   - Detection statistics (LLM vs regex)
   - Incident details table
   - Severity breakdown

3. **foundering_analysis.html** - Detailed foundering incident analysis
   - Fatality statistics per incident
   - Monthly trends
   - Interactive charts

4. **fatality_analysis.html** - Detailed fatality incident analysis
   - Fatalities by cause of death
   - Monthly trends
   - Incident details

## Detection Methods

### Regex Detection (Default)
If LLM dependencies are not installed, the system uses regex pattern matching:
- Fast processing (~500 incidents/second)
- Good accuracy (81-85%)
- No additional dependencies

### LLM-Enhanced Detection (Optional)
Install LLM dependencies for semantic understanding:

```bash
# Install LLM dependencies
pip install worldenergydata[llm]

# Or with UV
uv add worldenergydata --extra llm
```

Then run the analysis again - it will automatically use LLM detection:
- Semantic understanding of incident descriptions
- Higher accuracy (94-95%)
- Confidence scores and reasoning
- Slower processing (~100 incidents/second on CPU)

## Advanced Usage

### Python Script Direct Call

You can also call the Python report generator directly:

```bash
python3 scripts/marine_safety/generate_incident_report.py \
    --input-dir data/modules/marine_safety/input \
    --output-dir reports/marine_safety/custom_output \
    --use-llm true
```

**Arguments:**
- `--input-dir`: Directory containing incident CSV files
- `--output-dir`: Directory for output reports
- `--use-llm`: Use LLM detection (true/false)

### Customizing Input Data

1. Create your own CSV files in `data/modules/marine_safety/input/`
2. Follow the CSV format examples above
3. Run the bash script - it will automatically process your data

### Viewing Reports

The script outputs direct file paths to view in browser:

```
View the executive summary:
  file:///path/to/reports/marine_safety/20251022_200205/executive_summary.html
```

Copy and paste this URL into your browser to view the report.

## Report Features

### Executive Summary
- **Summary Cards**: Quick overview of incident counts
- **Key Findings**: Major insights from analysis
- **Recommendations**: Immediate, short-term, and long-term actions
- **Detection Statistics**: LLM vs regex comparison (if LLM enabled)

### Detailed Reports
- **Interactive Visualizations**: Plotly charts with hover, zoom, pan
- **Trend Analysis**: Monthly incident patterns
- **Severity Breakdown**: Incidents categorized by severity
- **Full Incident Tables**: Complete incident details

## Troubleshooting

### "Module not found" errors
Make sure you're running from the repository root:
```bash
cd /path/to/worldenergydata
bash scripts/marine_safety/analyze_incidents.sh
```

### "CSV file not found" warnings
Check that input files exist:
```bash
ls data/modules/marine_safety/input/
```

### LLM dependencies not installed
This is normal and expected. The system will use regex detection. To enable LLM:
```bash
pip install worldenergydata[llm]
```

### Reports not opening in browser
Copy the full `file://` URL from the script output and paste into your browser address bar.

## Example Output

```
=== Marine Safety Incident Analysis ===

Output directory: reports/marine_safety/20251022_200205

Checking LLM dependencies...
✓ LLM dependencies installed

Running marine safety incident analysis...

INFO: Loaded 30 hatch incidents
INFO: Loaded 15 foundering incidents
INFO: Loaded 20 fatality incidents
INFO: Analyzing incidents...
INFO: Initialized analyzer with LLM=True
INFO: Creating visualizations...
INFO: Generating reports...

=== Analysis Complete ===

Reports generated in: reports/marine_safety/20251022_200205

View the executive summary:
  file:///mnt/github/workspace-hub/worldenergydata/reports/marine_safety/20251022_200205/executive_summary.html
```

## For Developers

### Adding New Incident Types

1. Create CSV file in `data/modules/marine_safety/input/`
2. Update `load_incident_data()` in `generate_incident_report.py`
3. Create analysis function (e.g., `analyze_new_type()`)
4. Create visualization function
5. Update report generator

### Customizing Visualizations

All visualizations use Plotly - edit functions in `generate_incident_report.py`:
- `create_hatch_visualizations()`
- `create_foundering_visualizations()`
- `create_fatality_visualizations()`

### Customizing Report Templates

HTML templates are embedded in the report generator functions:
- `generate_executive_summary()`
- `generate_detailed_report()`

Edit these functions to customize report layout and styling.

## Support

For questions or issues:
- See `docs/modules/marine_safety/` for module documentation
- Check `examples/marine_safety/` for usage examples
- Review test cases in `tests/modules/marine_safety/analysis/`
