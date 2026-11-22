# Lease production aggregation

`ProductionProcessor.aggregate_by_lease` retains production when any grouping
key is missing. It returns a DataFrame for either record-list or DataFrame
input. This addresses the lease aggregation loss described in issue #1634.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| Initial | 2026-10-21 | Document retained incomplete groups and a conservation example. |

## Grouping contract

The composite key contains `lease_number` and each of `lease_name`,
`operator_name` and `district` that exists as an input column. Each output
volume is the sum of that column over rows sharing the composite key.
The same sum applies separately to oil, gas, water, condensate and supplied BOE.
No conversion coefficient or numerical acceptance tolerance is introduced.

Missing values (`None`, `NaN`, `pd.NA`) are retained as group keys. Records with
the same known values and the same missing-key positions combine; complete and
incomplete keys remain separate. Missing lease numbers are retained too, but
an unidentified group does not establish that its rows describe one real lease.
Names and districts are not inferred from other rows, and distinct known names,
operators or districts continue to split a lease number into separate groups.
Existing complete-key totals therefore remain unchanged.

This follows [pandas DataFrame.groupby, version 2.3, `dropna` and Examples](https://pandas.pydata.org/pandas-docs/version/2.3/reference/api/pandas.DataFrame.groupby.html)
(retrieved 2026-10-21): `dropna=False` includes missing values as group keys.
Direct aggregation does not normalize strings: an empty string is a literal
key distinct from a missing value. The preceding `process` step can normalize
blank or invalid districts to missing values. Validation during processing can
reject records before aggregation; retention applies to records supplied to
this method and does not change validation policy.

An omitted optional column contributes no key. Empty input, or input without
a `lease_number` column, keeps the existing pass-through behavior.

## Worked example

All values below are synthetic inputs. The expected answer is an independent
hand calculation, also recorded in
`tests/unit/texas_rrc/test_lease_aggregation_missing_keys.py`.

```python
import pandas as pd

from worldenergydata.texas_rrc.processors.production_processor import (
    ProductionProcessor,
)

records = [
    {"lease_number": "L1", "district": None, "oil_production": 100, "gas_production": 10},
    {"lease_number": "L1", "district": "7B", "oil_production": 200, "gas_production": 20},
    {"lease_number": "L1", "district": None, "oil_production": 300, "gas_production": 30},
    {"lease_number": "L2", "district": "7B", "oil_production": 50, "gas_production": 5},
]
result = ProductionProcessor().aggregate_by_lease(records)
assert len(result) == 3
assert result["oil_production"].sum() == 650
assert result["gas_production"].sum() == 65
unassigned = result[result["district"].isna()]
assert unassigned["oil_production"].item() == 400
assert unassigned["gas_production"].item() == 40
assert pd.DataFrame(records)["oil_production"].sum() == result["oil_production"].sum()
```

The method partitions the input into the following composite groups, treating
missing district as a retained key rather than removing those rows:

| Lease | District | Oil (BBL) | Gas (MCF) | Hand calculation |
| --- | --- | ---: | ---: | --- |
| L1 | missing | 400 | 40 | Oil 100 + 300; gas 10 + 30 |
| L1 | 7B | 200 | 20 | One input record |
| L2 | 7B | 50 | 5 | One input record |
| Total | | 650 | 65 | Oil 400 + 200 + 50; gas 40 + 20 + 5 |

The input totals are independently 100 + 200 + 300 + 50 = 650 BBL and
10 + 20 + 30 + 5 = 65 MCF. Retaining missing groups conserves both totals.
The regression suite also covers missing lease names, operator names and lease
numbers, repeated incomplete keys, nullable string columns, entirely missing
keys, literal empty names and processing with validation disabled.

## Limits

This method groups existing records; it does not reconcile lease identities,
fill missing metadata or qualify district codes. Other aggregation methods and
CSV district summaries are separate paths. BOE conversion provenance and missing
volume handling are outside this change.
