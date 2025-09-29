# BSEE Paleowells Module

This module provides comprehensive functionality for processing and analyzing paleontological well data from the Gulf of Mexico (GoM), integrating data from BSEE (Bureau of Safety and Environmental Enforcement) and BOEM (Bureau of Ocean Energy Management).

## Features

### 1. Data Processing (`data_processor.py`)
- Filter well data by geological epochs (Paleocene, Eocene, Oligocene)
- Parse fixed-width format paleo data files
- Analyze well distribution by geological epochs
- Generate comprehensive analysis reports

### 2. Data Downloading (`data_downloader.py`)
- Download BSEE/BOEM datasets:
  - Borehole raw data
  - Company information
  - Lease ownership data
  - Production data
  - Field information
- Automatic ZIP extraction
- Progress tracking for large downloads
- Dataset availability checking

### 3. Data Visualization (`visualizer.py`)
- Wells distribution by geological epoch
- Depth distribution analysis (True Vertical Depth and Measured Depth)
- Classification distribution (Definite vs Possible)
- Comprehensive visual reports

## Installation

The module is part of the worldenergydata package:

```bash
pip install -e .
```

## Usage

### Command Line Interface

The module can be used via command line:

```bash
# Process paleowells data
python -m worldenergydata.modules.bsee.paleowells process \
    --input-file raw_data.txt \
    --output-directory ./output \
    --analyze

# Download BSEE/BOEM data
python -m worldenergydata.modules.bsee.paleowells download \
    --datasets borehole company \
    --extract \
    --data-directory ./data

# Get info about available datasets
python -m worldenergydata.modules.bsee.paleowells download --info

# Visualize paleowells data
python -m worldenergydata.modules.bsee.paleowells visualize \
    --csv-file paleowells.csv \
    --output-directory ./figures \
    --report
```

### Python API

```python
from worldenergydata.modules.bsee.paleowells import (
    PaleowellsDataProcessor,
    BSEEDataDownloader,
    PaleowellsVisualizer
)

# Process data
processor = PaleowellsDataProcessor()
df = processor.process_paleowells_data(
    raw_data_file="raw_paleo_data.txt",
    output_directory="./processed"
)

# Download BSEE data
downloader = BSEEDataDownloader()
results = downloader.download_all_datasets(
    datasets=['borehole', 'company'],
    extract=True
)

# Create visualizations
visualizer = PaleowellsVisualizer()
figures = visualizer.create_comprehensive_report(df, "./figures")
```

## Data Sources

The module integrates data from:
- **BSEE**: https://www.data.bsee.gov
  - Borehole data
  - Production data
- **BOEM**: https://www.data.boem.gov
  - Company information
  - Lease ownership
  - Field data

## Geological Epochs

The module focuses on Lower Tertiary epochs:
- **Paleocene** (66-56 Ma)
- **Eocene** (56-34 Ma)
- **Oligocene** (34-23 Ma)

Additional epochs like Miocene and Pliocene are also recognized in the data.

## Output Files

### Processing Output
- `lower_tertiary_wells.txt` - Filtered well data
- `paleowells.csv` - Processed CSV format data
- `paleowells_analysis.json` - Analysis results

### Visualization Output
- `wells_by_epoch.png` - Bar chart of wells by epoch
- `true_vertical_depth_distribution.png` - TVD distribution
- `measured_depth_distribution.png` - MD distribution
- `classification_distribution.png` - Definite/Possible pie chart

## Testing

Run tests with pytest:

```bash
pytest tests/modules/bsee/paleowells/
```

## Data Format

### Fixed-Width Format Specification
The module processes fixed-width format files with the following structure:
- Record Type (1 char)
- API Well Number (12 chars)
- Paleo Report ID Number (2 chars)
- Total Number of Reports for API (2 chars)
- Measured Depth (5 chars)
- True Vertical Depth (5 chars)
- Definite/Possible (3 chars)
- At/In (2 chars)
- Paleo Age (100 chars)
- Definite/Possible_2 (3 chars)
- At/In_2 (2 chars)
- Ecozone (1 char)

## Integration with GoM Wells Legacy Code

This module modernizes and integrates functionality from the legacy GoM Wells codebase, providing:
- Improved error handling
- Configuration-based paths (no hardcoded paths)
- Comprehensive testing
- Modern Python patterns
- CLI interface
- Proper logging

## Future Enhancements

- [ ] Add support for additional geological epochs
- [ ] Integrate with GIS/mapping capabilities
- [ ] Add real-time data synchronization
- [ ] Support for additional BSEE/BOEM datasets
- [ ] Enhanced statistical analysis features
- [ ] Export to multiple formats (Excel, GeoJSON, etc.)

## License

Part of the worldenergydata project.