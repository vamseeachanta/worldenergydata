# Unit Conversion Catalog — worldenergydata

All conversion factors are defined in `units.py` in this directory.
This document is the human-readable reference.

## Oil — Liquid Volume

| From        | To          | Factor     | Standard / Note                             |
|-------------|-------------|------------|---------------------------------------------|
| `sm3`       | `bbl`       | 6.2898     | API MPMS Ch. 11 — 1 standard m³ crude oil  |
| `bbl`       | `sm3`       | 0.158987   | Inverse of SM3→BBL                         |
| `tonne_oil` | `bbl`       | 7.33       | API convention — ~35°API crude oil          |
| `bbl`       | `tonne_oil` | 0.136428   | Inverse of TONNE→BBL                       |
| `m3`        | `bbl`       | 6.2898     | Same as sm3→bbl at standard conditions     |

## Gas — Volume

| From       | To       | Factor     | Standard / Note                                     |
|------------|----------|------------|-----------------------------------------------------|
| `sm3_gas`  | `scf`    | 35.3147    | ISO 13443; GPA 2145 — 15 °C / 1 atm               |
| `msm3`     | `mmscf`  | 35.3147    | 1 million Sm³ → million standard cubic feet        |
| `msm3`     | `bcf`    | 0.0353147  | 1 million Sm³ → billion cubic feet                 |
| `mmscf`    | `mcf`    | 1000.0     | 1 MMscf = 1 000 Mcf (exact)                        |
| `mcf`      | `mmscf`  | 0.001      | Inverse of MMscf→Mcf                               |
| `bcf`      | `tcf`    | 0.001      | 1 BCF = 0.001 TCF (exact)                          |

## Water — Volume

| From       | To    | Factor  | Standard / Note                                  |
|------------|-------|---------|--------------------------------------------------|
| `m3`       | `bbl` | 6.2898  | 1 m³ water ≈ 1 bbl (density ≈ 1 t/m³)           |
| `tonne`    | `bbl` | 6.2898  | water density at surface ≈ 1.0 tonne/m³          |

## Pressure

| From  | To    | Factor     | Standard / Note                      |
|-------|-------|------------|--------------------------------------|
| `psi` | `bar` | 0.0689476  | NIST SP 811                          |
| `bar` | `psi` | 14.5038    | Inverse of PSI→BAR                   |
| `kpa` | `psi` | 0.145038   | 1 kPa = 0.145038 psi (NIST SP 811)  |

## Energy / Barrel of Oil Equivalent (BOE)

| From  | To    | Factor  | Standard / Note                                     |
|-------|-------|---------|-----------------------------------------------------|
| `bbl` | `boe` | 1.0     | 1 barrel crude oil ≡ 1 BOE (definition)             |
| `mcf` | `boe` | 0.178   | 6 MCF/BOE rule of thumb (SPE); ~1 BOE = 5.8 MMBTU  |
| `mwh` | `boe` | 0.5883  | 1 MWh ≈ 0.5883 BOE (derived from 5.8 MMBTU/BOE)    |

---

## Python Usage

### Scalar conversion

```python
from worldenergydata.common.units import convert

# 1 000 Sm³ crude oil → barrels
bbl = convert(1000.0, "sm3", "bbl")   # → 6289.8

# 3 000 psi → bar
bar = convert(3000.0, "psi", "bar")   # → 206.8
```

### Vectorised (pandas Series)

```python
from worldenergydata.common.units import convert_series

df["oil_bbl"] = convert_series(df["oil_sm3"], "sm3", "bbl")
```

### Importing class constants directly

```python
from worldenergydata.common.units import OilUnits, GasUnits

factor = OilUnits.SM3_TO_BBL          # 6.2898
mmscf  = GasUnits.MMSCF_TO_MCF        # 1000.0
```

### Programmatic lookup via UNIT_REGISTRY

```python
from worldenergydata.common.units import UNIT_REGISTRY

factor = UNIT_REGISTRY[("sm3", "bbl")]  # 6.2898
all_pairs = sorted(UNIT_REGISTRY)       # list all registered conversions
```

---

## Adding New Conversions

1. Add the class constant to the appropriate `*Units` class in `units.py`.
2. Add the `(from_unit, to_unit)` key-value pair to `UNIT_REGISTRY`.
3. Add a row to this catalog table.
4. Write tests in `tests/unit/common/test_units.py` covering the new pair.

---

*Generated for WRK-259. Maintained alongside `units.py`.*
