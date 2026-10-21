# Reporting incidence rates

`SafetyMetrics.calculate_trir()` and `calculate_ltir()` use the shared
`worldenergydata.hse.incidence_rate.incidence_rate` calculator. Invalid exposure
raises `ValueError`, including for zero cases. A measured zero requires known,
finite, positive employee-hours.

## Revision history

| Revision | Date | Change and reason |
| --- | --- | --- |
| 1 | 2026-10-21 | Document shared reporting calculations and exposure errors to prevent undefined rates being reported as zero. |

## Inputs and method

The [Cal/OSHA Brief Guide to Recordkeeping Requirements](https://www.dir.ca.gov/dosh/dosh_publications/RecKeepOverview.pdf),
2021 PDF revision, p. 5, “Calculating Injury and Illness Incidence Rates”, defines:

```text
incidence rate = qualified case count * 200,000 / actual employee-hours
```

The normalization represents annual hours for 100 employees working 40 hours
per week for 50 weeks, as specified on that page. The guide requires the case
count and hours to describe the same employee population and period. Its annual
summary worksheet excludes vacation, sick leave, holidays and other nonwork time,
even when paid. Include actual overtime hours.

| Reporting method | Selected count | Exposure |
| --- | --- | --- |
| `calculate_trir()` | `total_recordables` | `man_hours_worked` |
| `calculate_ltir()` | `lost_time_incidents` | `man_hours_worked` |

`incident_count` is not used in these rates. The caller must classify recordables
and the lost-time subset before calculation; the calculator does not infer them
from incident records. LTIR uses the same normalization with the caller's selected
lost-time cases. It does not automatically represent the broader DART category,
which also includes job transfer or restricted-duty cases.

When combining disjoint groups in the same period, sum counts and matching hours
before calculating. An arithmetic average of group rates does not generally give
the pooled rate. Matching population and period are caller responsibilities; the
numeric inputs contain no metadata that could verify them automatically.

## Validation and reporting callers

Counts must be nonnegative integers. Python integers and NumPy integral scalars,
including aggregation results, are accepted. Boolean, negative and nonintegral
counts raise `ValueError`. Arithmetic converts integral scalars to Python integers
before multiplication to avoid fixed-width overflow.

Exposure must be real, finite and strictly positive after conversion to a Python
float. Missing values, zero, negative values, NaN, infinities, booleans and non-real
values raise `ValueError`. An unrepresentable rate also raises `ValueError`.

The previous reporting methods returned zero for nonpositive exposure. Callers
must now supply qualified exposure or handle `ValueError` as an unavailable rate.
The default `SafetyMetrics()` retains placeholder zero hours, so invoking either
rate on it raises. Do not replace an unavailable rate with numeric zero.

`ComplianceTemplate.add_safety_compliance_metrics()` propagates the validation
error. It updates `context["safety_compliance"]` only after both rates succeed;
a failed update leaves any previous valid context unchanged. A caller catching
an error must avoid treating that previous context as newly calculated data.

## Worked example

All inputs in this example are synthetic. One employee population in one
reporting period has seven recordable cases, including two lost-time cases, and
400,000 actual employee-hours. Independent arithmetic using the cited equation:

```text
TRIR = 7 * 200,000 / 400,000 = 3.5 cases per 200,000 employee-hours
LTIR = 2 * 200,000 / 400,000 = 1.0 cases per 200,000 employee-hours
```

With the package available, run:

```sh
python examples/hse/reporting_incidence_rates.py
```

Expected output:

```text
TRIR: 3.5
LTIR: 1.0
Rate unavailable: supply finite, positive actual employee-hours.
```

No acceptance threshold or compliance conclusion is supplied. Exposure inference,
case classification and benchmark selection require separate qualified inputs.
