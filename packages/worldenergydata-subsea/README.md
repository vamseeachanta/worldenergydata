# worldenergydata-subsea

`subsea` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.subsea` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

## Component input validation

Rigid-jumper OD, wall thickness, length and pressure rating, and mooring size
and minimum breaking load must be finite and strictly positive. Optional
weights must be finite and nonnegative when supplied; zero is permitted.
Direct model construction and CSV loading apply the same checks and raise
Pydantic `ValidationError` for invalid values.

CSV loaders preserve literal text such as `NA`, `N/A`, `null` and `nan`.
Only empty cells are omitted: empty optional cells become `None`, while empty
required cells and NA-like text in numeric cells cause validation errors.
Supplier `get("")` and whitespace-only keys raise `ValueError`; nonblank keys
retain case-insensitive substring matching in CSV order.

```python
from worldenergydata.subsea.models.rigid_jumper import RigidJumperSpec

jumper = RigidJumperSpec(
    component_id="synthetic",
    manufacturer="NA",
    od_in=2,
    wall_thickness_in=0.5,
    length_ft=10,
    material_grade="synthetic",
    pressure_rating_psi=3,
    weight_air_kips=0,
    data_source="synthetic example",
)
assert jumper.length_ft == 10.0
assert jumper.weight_air_kips == 0.0
assert jumper.manufacturer == "NA"
```

Hand check: 2 in, 0.5 in, 10 ft and 3 psi are finite and greater than zero;
0 kips is finite and nonnegative. The corresponding mooring example uses
size 2 mm, minimum breaking load 3 kN and linear weight 0 kg/m. Ingestion
preserves these values in the field's stated units without conversion.
Both CSV cases are checked in
`tests/unit/subsea/test_component_numeric_contract.py`.

The examples are synthetic input checks, not catalog data or design limits.
Geometry consistency, capacity, source-unit qualification and catalog accuracy
are outside these checks. No engineering equation or standard coefficient is
introduced. Parser and finiteness references:
[pandas 2.3 `read_csv`, `keep_default_na` and `dtype`](https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.read_csv.html)
and [Python `math.isfinite`](https://docs.python.org/3/library/math.html#math.isfinite).
