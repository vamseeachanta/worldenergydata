# Technical Specification

This is the technical specification for the spec detailed in @specs/fatigue-sn-curve-database/spec.md

> Created: 2025-08-16
> Version: 1.0.0

## Technical Requirements

### Data Structure Requirements

- **S-N Curve Representation**
  - Bilinear curves on log-log scale (two-segment curves)
  - Single slope curves (simplified approach)
  - Multi-segment curves (for complex materials)
  - Parameters: log N = log A - m × log S format
  - Stress range (S) in MPa or ksi
  - Cycles to failure (N) as integer/float

- **Metadata Requirements**
  - Standard source (API RP 2A, DNV-RP-C203, ISO 19902, etc.)
  - Material specification (grade, yield strength, UTS)
  - Environment (air, seawater with/without CP, temperature)
  - Stress ratio (R = Smin/Smax)
  - Curve classification (base metal, weld classes, bolts)
  - Confidence levels (mean, design, characteristic)
  - Thickness correction factors

- **Standards Coverage**
  - API RP 2A-WSD (22nd Edition)
  - DNV-RP-C203 (Fatigue design of offshore structures)
  - ISO 19902 (Fixed offshore structures)
  - ABS Guide for Fatigue Assessment
  - NORSOK N-004 (Design of steel structures)
  - BS 7608 (Fatigue design and assessment)
  - IIW recommendations (welded joints)

### Data Model Architecture

```python
# Core S-N Curve Data Model
class SNcurve:
    curve_id: str  # Unique identifier
    standard: str  # e.g., "DNV-RP-C203"
    classification: str  # e.g., "C1", "D", "F3"
    material_type: str  # e.g., "carbon_steel", "stainless_steel"
    environment: str  # e.g., "seawater_cp", "air"
    
    # Curve parameters
    segments: List[Segment]  # Multiple segments for bilinear/multilinear
    stress_unit: str  # "MPa" or "ksi"
    
    # Metadata
    thickness_reference: float  # mm
    stress_ratio: float  # R value
    temperature_range: Tuple[float, float]  # °C
    confidence_level: str  # "mean", "design", "characteristic"
    
class Segment:
    log_a: float  # Intercept parameter
    m: float  # Slope parameter
    stress_range: Tuple[float, float]  # Valid stress range
    endurance_limit: Optional[float]  # Fatigue limit if applicable
```

### Data Collection Methodology

- **Primary Sources**
  - Direct extraction from PDF standards documents
  - Official digital supplements when available
  - Verified published amendments and corrections

- **Digitization Process**
  - Automated extraction using PDF parsing libraries
  - Manual verification against graphical curves
  - Cross-validation with published examples
  - Version control for standard updates

- **Quality Assurance**
  - Dual verification by independent extraction
  - Comparison with known benchmark cases
  - Validation against standard's example problems
  - Peer review of extracted datasets

## Approach Options

**Option A: Relational Database (PostgreSQL)**
- Pros: ACID compliance, complex queries, established tooling
- Cons: Requires database server, overhead for simple queries

**Option B: Document Store (MongoDB)**
- Pros: Flexible schema, easy to extend, JSON native
- Cons: Less efficient for numerical queries, requires MongoDB

**Option C: File-Based Storage (HDF5/Parquet)** (Selected)
- Pros: Portable, efficient for numerical data, no server required
- Cons: Limited concurrent access, manual indexing

**Rationale:** File-based storage selected for portability and ease of distribution. HDF5 provides efficient storage for numerical arrays while Parquet offers good compression and compatibility with data analysis tools.

## Implementation Architecture

### File Organization
```
worldenergydata/
├── src/
│   └── worldenergydata/
│       └── fatigue/
│           ├── __init__.py
│           ├── sn_curves.py  # Core module
│           ├── standards/
│           │   ├── api.py
│           │   ├── dnv.py
│           │   ├── iso.py
│           │   └── abs.py
│           └── data/
│               ├── sn_curves.parquet  # Main database
│               └── metadata.json  # Curve metadata
```

### API Design

```python
# Query Interface
from worldenergydata.fatigue import SNcurveDatabase

db = SNcurveDatabase()

# Get specific curve
curve = db.get_curve(standard="DNV-RP-C203", classification="D")

# Query by material
steel_curves = db.query(material_type="carbon_steel", 
                        environment="seawater_cp")

# Calculate life for given stress
N = curve.calculate_life(stress_range=150)  # MPa

# Get stress for target life
S = curve.calculate_stress(cycles=1e6)

# Export for external use
curve.export_json("output.json")
curve.export_csv("output.csv")
```

## External Dependencies

### Required Packages
- **pandas** (>=1.3.0) - Data manipulation and storage
  - Justification: Industry standard for tabular data
- **numpy** (>=1.21.0) - Numerical computations
  - Justification: Efficient array operations
- **pyarrow** (>=6.0.0) - Parquet file support
  - Justification: Efficient columnar storage format
- **scipy** (>=1.7.0) - Interpolation and curve fitting
  - Justification: Required for curve interpolation
- **pydantic** (>=2.0.0) - Data validation
  - Justification: Ensures data integrity and type safety

### Optional Dependencies
- **h5py** (>=3.0.0) - HDF5 format support
  - Justification: Alternative storage format
- **openpyxl** (>=3.0.0) - Excel export
  - Justification: Engineering tool compatibility

## Data Validation Strategy

### Validation Levels

1. **Schema Validation**
   - Required fields present
   - Data types correct
   - Value ranges reasonable

2. **Engineering Validation**
   - Monotonic decreasing curves
   - Stress > 0, Cycles > 0
   - Slope m typically 3-5 for steel
   - Intercept log A reasonable range

3. **Cross-Standard Validation**
   - Similar materials show similar trends
   - Known equivalencies maintained
   - Conservative hierarchy preserved

### Validation Implementation

```python
def validate_sn_curve(curve: SNcurve) -> ValidationResult:
    """Validate S-N curve data against engineering constraints"""
    checks = []
    
    # Check slope is within typical range
    for segment in curve.segments:
        if not (2.5 <= segment.m <= 5.5):
            checks.append(ValidationWarning(
                f"Slope m={segment.m} outside typical range"
            ))
    
    # Check curve is monotonic
    test_stresses = np.logspace(1, 3, 100)
    lives = [curve.calculate_life(s) for s in test_stresses]
    if not all(l1 >= l2 for l1, l2 in zip(lives, lives[1:])):
        checks.append(ValidationError("Non-monotonic curve"))
    
    return ValidationResult(checks)
```

## Performance Considerations

- **Load Time**: < 500ms for full database load
- **Query Performance**: < 10ms for single curve retrieval
- **Calculation Speed**: < 1ms per stress/life calculation
- **Memory Usage**: < 100MB for complete dataset
- **File Size**: Target < 10MB compressed

## Integration with External Tools

### DigitalModel Repository
```python
# Example integration
from worldenergydata.fatigue import SNcurveDatabase
from digitalmodel import FatigueAnalysis

# Load S-N curve
db = SNcurveDatabase()
sn_curve = db.get_curve(standard="API-RP-2A", classification="X")

# Use in digital model
analysis = FatigueAnalysis()
analysis.set_sn_curve(sn_curve.to_dict())
damage = analysis.calculate_damage(stress_history)
```

### Export Formats
- JSON: Full metadata and parameters
- CSV: Tabulated stress-life points
- HDF5: Numerical arrays for batch processing
- MATLAB: .mat files for engineering tools