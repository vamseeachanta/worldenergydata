# USWTDB offline turbine geometry

`worldenergydata.wind.load_uswtdb_csv` reads local CSV bytes using the retained
USWTDB release 3.2 contract, dated **14 October 2020**. This is a six-year-old
snapshot as of November 2026, not a current inventory. It provides reported
turbine geometry and location, without structural design qualification.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-11-22 | Define offline ingestion and validation for the retained release. |

## Retained source basis

The inputs are already retained under `data/modules/wind/`. No source records
are added by this change; test records are synthetic. No live service or
redistribution terms have been verified. The codebook supplies the field types,
units and non-missing counts; the CSV represents missing optional values with
empty cells. The supported columns' observed non-empty counts match the
codebook. No numeric sentinel meaning is inferred.

| Input | SHA-256 |
| --- | --- |
| `uswtdbCSV.zip` | `e9c86fa246d4e86f84cba153aa596927e1598b6c2e1017e57cc70ad58bacc57a` |
| CSV member `uswtdb_v3_2_20201014.csv` | `4f0c6f6956001aaa81a958dd141d3ead7ef6d28361a4511449a855531384961c` |
| `uswtdb_v3_2_20201014_codebook.xlsx` | `72c37d22798d2041342f81248cf6e2014db81ea846d6df33428a9309a655b65e` |

## Supported schema

All headers below must occur exactly once. Their order may vary; additional
columns are accepted but not exposed. Field names and units remain those of the
codebook; no unit conversion or geometry inference occurs.

| Field | Returned type | Meaning and unit | Empty cell |
| --- | --- | --- | --- |
| `case_id` | `str` | Unique USWTDB identifier | Rejected |
| `faa_ors` | `str` | Obstacle repository identifier | `None` |
| `faa_asn` | `str` | Aeronautical study identifier | `None` |
| `usgs_pr_id` | `str` | Prior turbine identifier | `None` |
| `eia_id` | `str` | Plant identifier | `None` |
| `t_cap` | `int` | Turbine capacity, kW | `None` |
| `t_hh` | `float` | Hub height, meters | `None` |
| `t_rd` | `float` | Rotor diameter, meters | `None` |
| `t_rsa` | `float` | Rotor swept area, square meters | `None` |
| `t_ttlh` | `float` | Source-calculated total height, meters | `None` |
| `xlong` | `float` | Longitude, NAD83 decimal degrees | Rejected |
| `ylat` | `float` | Latitude, NAD83 decimal degrees | Rejected |

Identifiers preserve their text, including leading zeros. Integer identifiers
and capacity accept ASCII digits only. Other numbers accept a dot decimal
separator and optional exponent; grouped thousands, decimal commas, whitespace,
non-finite values and numeric overflow are rejected. Measurements must be
nonnegative; longitude must be within [-180, 180], latitude within [-90, 90].
These are parser checks, not physical plausibility or survey accuracy checks.
Reported zero remains zero. An empty optional cell alone becomes `None`;
placeholder strings and negative sentinels are not treated as missing.

## Usage and error handling

```python
from pathlib import Path
from zipfile import ZipFile

from worldenergydata.wind import load_uswtdb_csv

with ZipFile(Path("data/modules/wind/uswtdbCSV.zip")) as archive:
    data = load_uswtdb_csv(archive.read("uswtdb_v3_2_20201014.csv"))
print(data.release, len(data.turbines), data.source_sha256)
```

The retained CSV reads as **65,548 records**. The result contains immutable
records in source order, the declared release contract and the SHA-256 of the
exact supplied bytes (including a UTF-8 BOM if present). The release is a parser
contract label, not automatic input-version detection or digest authentication;
compare the digest above when reading the retained source.

Invalid UTF-8, missing or duplicate headers, inconsistent row widths, blank
records, duplicate `case_id` values and invalid numeric values raise `ValueError`.
Row errors identify the physical CSV line and affected field without echoing
source values. No partial dataset is returned. Empty datasets are rejected.

Live API access, dataset refresh, GIS exports, foundation and material
properties, confidence filtering and structural qualification remain outside
this reader. Other source fields, including confidence flags, are not exposed.
The broader structural-data request remains open in #2.
