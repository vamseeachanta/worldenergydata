# Independent production arithmetic benchmarks

The revision 1 benchmarks qualify arithmetic and summary selection using
independent hand calculations. Every input is synthetic. They do not qualify
measured production, source revisions for live datasets, or current fiscal law.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-21 | Add independent hand answers, direct DPR summaries and an explicit zero-reference contract to prevent implicit acceptance. |

## Source basis

- EIA, [Drilling Productivity Report: Report Background and Methodological Overview](https://www.eia.gov/petroleum/drilling/pdf/dpr_methodology.pdf),
  August 2014, updated February 2019, p. 18, **Production net change**:
  net change = new-well production forecast + legacy production change.
  The signed legacy change is negative for decline. These are changes in daily
  production rate, not monthly production volumes.
- [PEP 485](https://peps.python.org/pep-0485/), 2015, **Symmetry** and
  **Behavior near zero**: a known reference can define the relative scale;
  comparisons against zero need a use-specific absolute tolerance.
  This benchmark uses BSEE as the reference. It does not use the symmetric
  `math.isclose` relative scale or any default tolerance from that function.
- NIST, [SP 811, Guide for the Use of the International System of Units](https://nvlpubs.nist.gov/nistpubs/Legacy/SP/nistspecialpublication811e2008.pdf),
  2008 edition, section 4, Table 5: kilo means a factor of 1000.
  Thus 40 bbl/day is 0.04 thousand bbl/day (kbd).

All three public documents were opened successfully on 2026-10-21. The EIA
document is a historical method reference. No live-production dataset is used.
The downloaded EIA document SHA-256 is
`d0876f1dbc4a6b631face3accf4b424e7f19c894c0072043eb2f3a18152730b5`.
The downloaded NIST document SHA-256 is
`788dd8f0bcb0ec06e40c300690266742532a7e760a93be57764b77ed0ef3482f`.

## Crosscheck contract

For EIA rate E and BSEE reference B, both in kbd:

- Signed difference d = E - B, in kbd.
- For B greater than zero, relative difference r = abs(d) / B, dimensionless.
- For B equal to zero, relative difference is undefined and returned as `None`.
- Exact equality passes, including zero/zero.
- Otherwise, supplied absolute tolerance A passes when abs(d) <= A.
- For a nonzero B, supplied relative tolerance R also passes when r <= R.
- If both limits apply, either can establish agreement. If applicable limits
  all fail, the result is `FAIL`. Without an applicable limit it is
  `NOT_EVALUATED`, and `within_tolerance` is `None`.

The equality and tolerance rules are explicit comparison policy, based on the
PEP 485 discussion above. No numerical acceptance limit is recommended.
Production and tolerances must be finite and nonnegative; invalid inputs raise
`ValueError` instead of returning an agreement decision.

| Output | Units or meaning |
| --- | --- |
| `eia_kbd`, `bsee_kbd`, `difference_kbd` | thousand bbl/day |
| `pct_difference` | dimensionless fraction, retained legacy key; `None` when B is zero |
| `relative_tolerance_fraction` | supplied dimensionless fraction, or `None` |
| `absolute_tolerance_kbd` | supplied thousand bbl/day, or `None` |
| `within_tolerance` | `True`, `False`, or `None` |
| `status` | `PASS`, `FAIL`, or `NOT_EVALUATED` |

Migration: `GoMCrosscheck()` no longer supplies the unsupported implicit
relative tolerance. A caller whose application has independently justified a
5.0 % limit must pass `GoMCrosscheck(tolerance_pct=0.05)` explicitly. The legacy
parameter and result names containing `pct` still mean a fraction, not a
percentage-point value. Callers must handle `None` for undefined relative
differences and indeterminate decisions. Tolerances do not establish matching
reporting periods, commodity definitions, geographic coverage or source vintage.

## Worked crosscheck example

These synthetic inputs and limits are chosen for the benchmark, not taken from
an operating dataset. Hand calculation: 105 - 100 = 5 kbd; 5/100 = 0.05, or
5.0 %. A caller-selected 5.0 % relative limit therefore passes at equality.
At a zero reference, 0.04 - 0 = 0.04 kbd has no relative error. It is not
evaluated unless an absolute tolerance is supplied. A synthetic 0.03 kbd
absolute limit fails; a synthetic 0.04 kbd absolute limit passes at equality.

```pycon
>>> from worldenergydata.eia_us.analysis.us_fiscal import GoMCrosscheck
>>> result = GoMCrosscheck(tolerance_pct=0.05).compare(105.0, 100.0)
>>> (result["difference_kbd"], result["pct_difference"], result["status"])
(5.0, 0.05, 'PASS')
>>> result = GoMCrosscheck(tolerance_pct=0.05).compare(0.04, 0.0)
>>> (result["pct_difference"], result["within_tolerance"], result["status"])
(None, None, 'NOT_EVALUATED')
>>> GoMCrosscheck(absolute_tolerance_kbd=0.03).compare(0.04, 0.0)["status"]
'FAIL'
>>> GoMCrosscheck(absolute_tolerance_kbd=0.04).compare(0.04, 0.0)["status"]
'PASS'
>>> result = GoMCrosscheck().compare(0.0, 0.0)
>>> (result["pct_difference"], result["within_tolerance"], result["status"])
(None, True, 'PASS')

```

## Worked DPR example

Inputs: two unsorted monthly records for synthetic basin A. New-well input is
the aggregate new-well contribution in bbl/day. It must not be a per-rig or
per-well productivity value. Rig count is measured in rigs. Period strings use
the existing normalized `YYYY-MM` convention.

Method: the EIA p. 18 equation gives 120 + (-45) = 75 bbl/day and
50 + (-50) = 0 bbl/day. Latest-period selection gives February's 4 rigs,
even though January's count is larger. No engineering coefficients or
floating-point acceptance limits are needed for these integer-valued answers.

```pycon
>>> from worldenergydata.eia_us.production.drilling_productivity import DrillingProductivityReport
>>> report = DrillingProductivityReport()
>>> records = [
...     {"period": "2024-02", "basin": "A", "rig_count": "4",
...      "new_well_ip_bopd": "120", "legacy_decline_bopd": "-45",
...      "total_production_bopd": "1075"},
...     {"period": "2024-01", "basin": "A", "rig_count": "9",
...      "new_well_ip_bopd": "50", "legacy_decline_bopd": "-50",
...      "total_production_bopd": "1000"},
... ]
>>> data = report.load_all_basins(records)
>>> report.net_change_summary(data)["net_change_bopd"].tolist()
[75.0, 0.0]
>>> report.rig_count_summary(data).to_dict("records")
[{'basin': 'A', 'period': '2024-02', 'rig_count': 4.0}]

```

## Test coverage and limits

`tests/unit/eia_us/test_gom_crosscheck.py` records the revision 1 hand calculations
and tests inclusive limits, signed differences, zero/zero, nonzero/zero,
missing tolerances, either-limit agreement and invalid numeric inputs.
`tests/unit/eia_us/test_drilling_productivity.py` independently checks numeric
normalization, latest-period selection, descending rig-count order, positive,
negative and zero net change, empty schemas and preservation of the input frame.
The expectations are literal hand answers; neither a second call to the code
under test nor a stored program output supplies them.

The examples above are executable with `python -m doctest` on this document
with the package available on the import path. Tests and examples run offline.
The existing loader missingness, unit/calendar validation and annual aggregation
work remains separate (#1605). These benchmarks assume complete normalized
records and unique basin-period rows. Missing, duplicate and invalid dates are
not newly qualified. Decline modeling (#1604), API transport/cache isolation
(#1606), live source qualification (#462) and fiscal provenance (#361) remain
separate work.
