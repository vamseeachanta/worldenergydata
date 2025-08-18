# API Specification

This is the API specification for the spec detailed in @specs/fatigue-sn-curve-database/spec.md

> Created: 2025-08-16
> Version: 1.0.0

## API Overview

The Fatigue S-N Curve API provides programmatic access to engineering-quality fatigue data from industry standards. It supports querying, calculation, and export operations for integration with analysis tools.

## Core Classes

### SNcurveDatabase

Main interface for accessing the S-N curve database.

```python
class SNcurveDatabase:
    def __init__(self, data_path: Optional[str] = None):
        """Initialize database with optional custom data path"""
    
    def get_curve(self, standard: str, classification: str, 
                  environment: Optional[str] = None) -> SNcurve:
        """Retrieve specific S-N curve by standard and classification"""
    
    def query(self, **filters) -> List[SNcurve]:
        """Query curves by multiple criteria"""
    
    def list_standards(self) -> List[str]:
        """Get list of available standards"""
    
    def list_classifications(self, standard: str) -> List[str]:
        """Get classifications for a specific standard"""
```

### SNcurve

Represents a single S-N curve with calculation methods.

```python
class SNcurve:
    # Properties
    curve_id: str
    standard: str
    classification: str
    material_type: str
    environment: str
    segments: List[Segment]
    metadata: Dict[str, Any]
    
    # Methods
    def calculate_life(self, stress_range: float, 
                       thickness: Optional[float] = None) -> float:
        """Calculate cycles to failure for given stress range"""
    
    def calculate_stress(self, cycles: float,
                        thickness: Optional[float] = None) -> float:
        """Calculate allowable stress for target life"""
    
    def apply_thickness_correction(self, thickness: float) -> 'SNcurve':
        """Return new curve with thickness correction applied"""
    
    def to_dict(self) -> Dict:
        """Export curve as dictionary"""
    
    def to_dataframe(self, n_points: int = 100) -> pd.DataFrame:
        """Generate tabulated S-N data points"""
```

## Query API

### Filter Parameters

```python
# Query by material
curves = db.query(
    material_type="carbon_steel",  # Material category
    yield_strength=(350, 450),     # Range in MPa
    environment="seawater_cp"      # Environmental condition
)

# Query by standard
curves = db.query(
    standard="DNV-RP-C203",
    confidence_level="design",
    thickness_range=(25, 100)  # mm
)

# Complex queries
curves = db.query(
    standard=["API-RP-2A", "ISO-19902"],
    classification=["D", "E", "F"],
    environment=["air", "seawater_cp"],
    stress_ratio=(-1, 0.5)  # R ratio range
)
```

### Response Format

```python
# Single curve response
{
    "curve_id": "DNV-RP-C203-D-SW-CP",
    "standard": {
        "name": "DNV-RP-C203",
        "version": "2016",
        "section": "5.3"
    },
    "classification": "D",
    "material": {
        "type": "carbon_steel",
        "grade": "S355",
        "yield_strength": 355,
        "tensile_strength": 490
    },
    "environment": {
        "medium": "seawater",
        "cathodic_protection": true,
        "temperature": [-10, 50]
    },
    "segments": [
        {
            "log_a": 12.164,
            "m": 3.0,
            "stress_range": [52.63, 1000],
            "cycles_range": [1e4, 1e7]
        },
        {
            "log_a": 15.606,
            "m": 5.0,
            "stress_range": [0, 52.63],
            "cycles_range": [1e7, 1e9]
        }
    ]
}
```

## Calculation Methods

### Life Calculation

```python
# Basic calculation
curve = db.get_curve("DNV-RP-C203", "D")
cycles = curve.calculate_life(stress_range=150)  # MPa

# With thickness correction
cycles = curve.calculate_life(
    stress_range=150,
    thickness=50  # mm, applies (tref/t)^0.25 correction
)

# Batch calculation
stress_history = [120, 150, 180, 200]
lives = [curve.calculate_life(s) for s in stress_history]
```

### Stress Calculation

```python
# Allowable stress for target life
stress = curve.calculate_stress(cycles=2e6)

# Design curve with safety factor
design_curve = curve.apply_safety_factor(factor=2.0)
design_stress = design_curve.calculate_stress(cycles=2e6)
```

### Damage Calculation

```python
# Palmgren-Miner cumulative damage
stress_blocks = [
    {"stress": 150, "cycles": 1e5},
    {"stress": 120, "cycles": 5e5},
    {"stress": 100, "cycles": 1e6}
]

damage = curve.calculate_damage(stress_blocks)
# damage > 1.0 indicates failure
```

## Export Methods

### JSON Export

```python
# Full curve data
curve.export_json("curve_data.json", include_metadata=True)

# Simplified format for web API
json_data = curve.to_json(simplified=True)
```

### CSV Export

```python
# Tabulated S-N points
df = curve.to_dataframe(n_points=50)
df.to_csv("sn_curve.csv")

# Multiple curves comparison
curves = db.query(standard="API-RP-2A")
comparison_df = pd.DataFrame([
    c.to_dataframe(n_points=20) for c in curves
])
```

### Integration Export

```python
# For digitalmodel repository
digital_model_format = {
    "curve_type": "sn_fatigue",
    "parameters": curve.get_parameters(),
    "valid_range": curve.get_stress_range(),
    "metadata": curve.metadata
}

# For FEA software
ansys_format = curve.export_ansys()
abaqus_format = curve.export_abaqus()
```

## Batch Operations

```python
# Batch processing
def analyze_materials(material_list):
    results = {}
    for material in material_list:
        curves = db.query(material_type=material)
        results[material] = {
            "count": len(curves),
            "standards": [c.standard for c in curves],
            "min_endurance": min(c.endurance_limit for c in curves)
        }
    return results

# Parallel processing
from concurrent.futures import ThreadPoolExecutor

def calculate_lives_parallel(curve, stress_history):
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(curve.calculate_life, s) 
                  for s in stress_history]
        return [f.result() for f in futures]
```

## Error Handling

```python
from worldenergydata.fatigue.exceptions import (
    CurveNotFoundError,
    InvalidStressError,
    ExtrapolationWarning
)

try:
    curve = db.get_curve("DNV-RP-C203", "Z")
except CurveNotFoundError as e:
    print(f"Curve not found: {e}")
    available = db.list_classifications("DNV-RP-C203")
    print(f"Available classifications: {available}")

try:
    life = curve.calculate_life(stress_range=-100)
except InvalidStressError:
    print("Stress must be positive")

# Handle extrapolation
with warnings.catch_warnings():
    warnings.filterwarnings("error", category=ExtrapolationWarning)
    try:
        life = curve.calculate_life(stress_range=1000)
    except ExtrapolationWarning:
        print("Stress outside curve range")
```

## Performance Specifications

- **Single curve retrieval**: < 10ms
- **Batch query (100 curves)**: < 100ms
- **Life calculation**: < 1ms per point
- **DataFrame generation (100 points)**: < 50ms
- **JSON serialization**: < 20ms