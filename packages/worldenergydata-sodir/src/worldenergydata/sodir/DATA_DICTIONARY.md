# SODIR Data Dictionary

## Field Name to NPD Field Code Mapping

| Field Name     | NPD Field Code | Status    | Operator          |
|----------------|----------------|-----------|-------------------|
| EDVARD GRIEG   | 25245833       | PRODUCING | Aker BP           |
| VALHALL        | 43765          | PRODUCING | Aker BP           |
| IVAR AASEN     | 25245851       | PRODUCING | Aker BP           |
| SOLVEIG        | 31175335       | PRODUCING | Equinor           |
| EKOFISK        | 43506          | PRODUCING | ConocoPhillips    |
| TROLL          | 46437          | PRODUCING | Equinor           |
| JOHAN SVERDRUP | 26376286       | PRODUCING | Equinor           |
| OSEBERG        | 43633          | PRODUCING | Equinor           |
| GULLFAKS       | 43686          | PRODUCING | Equinor           |
| SNORRE         | 43718          | PRODUCING | Equinor           |
| STATFJORD      | 43658          | PRODUCING | Equinor           |
| MARTIN LINGE   | 20460988       | PRODUCING | Equinor           |
| BREIDABLIKK    | 31164279       | PRODUCING | Equinor           |
| SLEIPNER       | 43795          | PRODUCING | Equinor           |
| DRAUGEN        | 43771          | PRODUCING | OKEA              |
| NORNE          | 43814          | PRODUCING | Equinor           |

## Units

| Abbreviation | Full Name                     | System   | Notes                    |
|-------------|-------------------------------|----------|--------------------------|
| Sm3         | Standard cubic meter          | Metric   | At 15 deg C, 1 atm       |
| MSm3        | Million standard cubic meters | Metric   | 1e6 Sm3                  |
| BSm3        | Billion standard cubic meters | Metric   | 1e9 Sm3                  |
| bbl         | Barrel of oil                 | Imperial | 158.987 liters            |
| MMbbl       | Million barrels               | Imperial | 1e6 bbl                  |
| Mcf         | Thousand cubic feet           | Imperial | Gas volume                |
| MMcf        | Million cubic feet            | Imperial | 1e6 cf                   |
| BCF         | Billion cubic feet            | Imperial | 1e9 cf                   |
| BOE         | Barrel of oil equivalent      | Mixed    | 1 BOE = 5800 cf gas      |
| NOK         | Norwegian Krone               | Currency | Norwegian currency        |
| USD         | United States Dollar          | Currency | US currency               |

## Conversion Factors

| From        | To           | Factor     | Notes                        |
|-------------|-------------|------------|------------------------------|
| 1 Sm3 oil   | bbl         | 6.2898     | Standard SODIR conversion    |
| 1 MSm3 gas  | Mcf         | 35.3147    | At standard conditions       |
| 1 BSm3 gas  | BCF         | 35.3147    | Same ratio scaled            |
| 1 bbl       | Sm3         | 0.15899    | Inverse of 6.2898            |
| 1 BCF       | BSm3        | 0.02832    | Inverse of 35.3147           |
| 1 BOE       | Sm3         | 0.15899    | Oil equivalent basis         |

## Column Name Conventions

### Monthly Production (from SODIR API)

| Raw API Field                        | Processed Field         | Unit      |
|--------------------------------------|------------------------|-----------|
| fldName                              | field_name             | text      |
| prfYear                              | year                   | integer   |
| prfMonth                             | month                  | integer   |
| prfPrdOilNetMillSm3                  | oil_sm3                | Sm3       |
| prfPrdGasNetBillSm3                  | gas_sm3                | Sm3       |
| prfPrdNGLNetMillSm3                  | ngl_sm3                | Sm3       |
| prfPrdCondensateNetMillSm3           | condensate_sm3         | Sm3       |
| prfPrdOeNetMillSm3                   | oe_sm3                 | Sm3       |
| prfPrdProducedWaterInFieldMillSm3    | water_injected_sm3     | Sm3       |

### Field Data (from SODIR API)

| Raw API Field                   | Processed Field                       | Unit   |
|--------------------------------|---------------------------------------|--------|
| fldName                        | field_name                            | text   |
| fldNpdidField                  | field_id                              | text   |
| fldStatus                      | status                                | text   |
| fldOperatorName                | operator                              | text   |
| fldDiscoveryYear               | discovery_year                        | int    |
| fldProductionStartYear         | production_start_year                 | int    |
| fldOriginalReservesOil         | original_reserves_oil_mmbbl           | MMbbl  |
| fldRemainingReservesOil        | remaining_reserves_oil_mmbbl          | MMbbl  |
| fldRecoverableOil              | recoverable_oil_mmbbl                 | MMbbl  |
| fldCumulativeOilProduction     | cumulative_oil_production_mmbbl       | MMbbl  |
| fldCumulativeGasProduction     | cumulative_gas_production_bcf         | BCF    |
| fldCumulativeWaterInjection    | cumulative_water_injected_sm3         | MSm3   |
