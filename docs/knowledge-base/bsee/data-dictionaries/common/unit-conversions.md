# Unit Conversions

> **Usage**: Standard measurement units in BSEE data
> **Critical**: Production in BBL (oil) and MCF (gas)
> **Note**: All BSEE depths are in feet; pressures in PSI

---

## Quick Reference - Production Units

| Unit | Name | Equivalent | Used For |
|------|------|------------|----------|
| BBL | Barrel | 42 US gallons | Oil, condensate, water |
| MCF | Thousand Cubic Feet | 1,000 ft³ | Gas (standard) |
| MMCF | Million Cubic Feet | 1,000 MCF | Gas (monthly totals) |
| BCF | Billion Cubic Feet | 1,000 MMCF | Gas (annual/field) |
| TCF | Trillion Cubic Feet | 1,000 BCF | Gas (reserves) |
| BOE | Barrel Oil Equivalent | 1 BBL or 6 MCF | Combined reporting |

---

## Oil/Liquid Units

### Volume Conversions

| From | To | Factor |
|------|----|----|
| 1 BBL | Gallons (US) | 42 |
| 1 BBL | Liters | 158.987 |
| 1 BBL | Cubic meters | 0.15899 |
| 1 MBbl | BBL | 1,000 |
| 1 MMBbl | BBL | 1,000,000 |

### BSEE Production Fields

| Field | Unit | Description |
|-------|------|-------------|
| OIL_PROD | BBL | Monthly oil production |
| COND_PROD | BBL | Monthly condensate |
| WATER_PROD | BBL | Monthly water |
| OIL_DISP | BBL | Oil disposed |

### Conversion Code

```python
def bbl_to_liters(bbl):
    return bbl * 158.987

def bbl_to_cubic_meters(bbl):
    return bbl * 0.15899

def mbbl_to_bbl(mbbl):
    return mbbl * 1000
```

---

## Gas Units

### Volume Conversions

| From | To | Factor |
|------|----|----|
| 1 MCF | Cubic feet | 1,000 |
| 1 MMCF | MCF | 1,000 |
| 1 BCF | MMCF | 1,000 |
| 1 TCF | BCF | 1,000 |
| 1 MCF | Cubic meters | 28.317 |

### Gas Scale Reference

| Unit | Cubic Feet | Typical Use |
|------|------------|-------------|
| MCF | 10³ | Well daily rate |
| MMCF | 10⁶ | Well monthly |
| BCF | 10⁹ | Field annual |
| TCF | 10¹² | Basin reserves |

### BSEE Gas Fields

| Field | Unit | Description |
|-------|------|-------------|
| GAS_PROD | MCF | Monthly gas production |
| GAS_LIFT | MCF | Gas used for lift |
| GAS_FLARE | MCF | Gas flared |
| GAS_SOLD | MCF | Gas sold |

### Conversion Code

```python
def mcf_to_mmcf(mcf):
    return mcf / 1000

def mmcf_to_bcf(mmcf):
    return mmcf / 1000

def mcf_to_cubic_meters(mcf):
    return mcf * 28.317
```

---

## Barrel of Oil Equivalent (BOE)

### Standard Conversion

| Ratio | Description |
|-------|-------------|
| 6 MCF = 1 BOE | Energy equivalent (approximate) |
| 5.8 MCF = 1 BOE | EIA standard |
| 6.0 MCF = 1 BOE | BSEE/industry common |

### BOE Calculation

```python
def calculate_boe(oil_bbl, gas_mcf, ratio=6.0):
    """Calculate BOE from oil and gas volumes."""
    gas_boe = gas_mcf / ratio
    return oil_bbl + gas_boe

# Example
oil = 10000  # BBL
gas = 60000  # MCF
boe = calculate_boe(oil, gas)  # 20,000 BOE
```

### BOE/D (Daily Rate)

| Production | BOE/D Classification |
|------------|---------------------|
| < 100 | Marginal |
| 100-1,000 | Small |
| 1,000-10,000 | Medium |
| > 10,000 | Large |

---

## Depth Units

### BSEE Standard: Feet

| Unit | Conversion |
|------|------------|
| 1 foot | 0.3048 meters |
| 1 meter | 3.2808 feet |

### Depth Fields

| Field | Unit | Description |
|-------|------|-------------|
| TOTAL_DEPTH | feet | Total measured depth |
| TVD | feet | True vertical depth |
| WATER_DEPTH | feet | Water depth at location |
| TOP_PERF | feet | Top perforation depth |
| BOT_PERF | feet | Bottom perforation depth |
| MD | feet | Measured depth |

### Depth Conversion

```python
def feet_to_meters(feet):
    return feet * 0.3048

def meters_to_feet(meters):
    return meters * 3.2808

# Example: 15,000 ft well
depth_ft = 15000
depth_m = feet_to_meters(depth_ft)  # 4,572 m
```

---

## Pressure Units

### BSEE Standard: PSI

| Unit | Full Name | Description |
|------|-----------|-------------|
| PSI | Pounds per Square Inch | Gauge pressure |
| PSIA | PSI Absolute | Absolute pressure |
| PSIG | PSI Gauge | Relative to atmosphere |

### Relationship

```
PSIA = PSIG + 14.7 (atmospheric pressure at sea level)
```

### Pressure Conversions

| From | To | Factor |
|------|----|----|
| 1 PSI | kPa | 6.895 |
| 1 PSI | bar | 0.06895 |
| 1 PSI | atm | 0.06805 |
| 1 bar | PSI | 14.504 |

### Pressure Fields

| Field | Unit | Description |
|-------|------|-------------|
| BHP | PSIA | Bottom hole pressure |
| SIWHP | PSIG | Shut-in wellhead pressure |
| FTP | PSIG | Flowing tubing pressure |
| CASING_PRESS | PSIG | Casing pressure |

### Conversion Code

```python
def psi_to_kpa(psi):
    return psi * 6.895

def psig_to_psia(psig, atm=14.7):
    return psig + atm

def psia_to_psig(psia, atm=14.7):
    return psia - atm
```

---

## Temperature Units

### BSEE Standard: Fahrenheit

| Conversion | Formula |
|------------|---------|
| F to C | C = (F - 32) * 5/9 |
| C to F | F = C * 9/5 + 32 |

### Temperature Fields

| Field | Unit | Description |
|-------|------|-------------|
| BHT | °F | Bottom hole temperature |
| SURFACE_TEMP | °F | Surface temperature |

### Conversion Code

```python
def fahrenheit_to_celsius(f):
    return (f - 32) * 5 / 9

def celsius_to_fahrenheit(c):
    return c * 9 / 5 + 32

# Example: 250°F bottom hole temp
bht_f = 250
bht_c = fahrenheit_to_celsius(bht_f)  # 121.1°C
```

---

## Common Conversion Table

| Convert | From | To | Multiply By |
|---------|------|----|----|
| Oil volume | BBL | Liters | 158.987 |
| Oil volume | BBL | m³ | 0.15899 |
| Gas volume | MCF | m³ | 28.317 |
| Depth | feet | meters | 0.3048 |
| Pressure | PSI | kPa | 6.895 |
| Pressure | PSI | bar | 0.06895 |
| Temperature | °F | °C | (F-32)*5/9 |

---

## Python Utility Module

```python
"""BSEE Unit Conversions"""

# Volume
BBL_TO_LITERS = 158.987
BBL_TO_M3 = 0.15899
MCF_TO_M3 = 28.317
MCF_PER_BOE = 6.0

# Length
FEET_TO_METERS = 0.3048

# Pressure
PSI_TO_KPA = 6.895
PSI_TO_BAR = 0.06895
ATM_PSI = 14.7

class BSEEUnits:
    @staticmethod
    def oil_bbl_to_m3(bbl):
        return bbl * BBL_TO_M3

    @staticmethod
    def gas_mcf_to_m3(mcf):
        return mcf * MCF_TO_M3

    @staticmethod
    def calculate_boe(oil_bbl, gas_mcf):
        return oil_bbl + (gas_mcf / MCF_PER_BOE)

    @staticmethod
    def depth_ft_to_m(feet):
        return feet * FEET_TO_METERS

    @staticmethod
    def pressure_psig_to_psia(psig):
        return psig + ATM_PSI
```

---

## Related Documents

- [Production Fields](../production/production-fields.md) - Production units
- [Borehole Fields](../wells/borehole-fields.md) - Depth/pressure units
- [Date Formats](date-formats.md) - Time-based reporting
