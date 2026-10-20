# Compliance chart inputs and worked example

The compliance dashboard preserves valid measurements and marks missing or
invalid metrics `NOT_EVALUATED`. Partial quota data produces gaps with the
missing field names displayed. This guide describes presentation behavior;
the existing score policies do not establish regulatory acceptance.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 1 | 2026-10-20 | Documented input handling and a synthetic example to reproduce the compliance chart fixes. |

## Input contract

`ComplianceTemplate.generate_compliance_visualizations(data)` and
`ComplianceTemplate._create_compliance_dashboard(data)` use the same renderer.
`ComplianceTemplate.get_compliance_status_color(score)` exposes the existing
color lookup from `compliance_calculations.py`.

| Field | Meaning | Valid input |
| --- | --- | --- |
| `production_compliance` | Actual production divided by permitted production, expressed as a percentage | Finite, nonnegative real number; overproduction remains visible |
| `environmental_score`, `safety_score`, `overall_compliance_score` | Existing normalized scores | Finite real number in the unit interval |
| `oil_quota`, `oil_actual` | Oil volume in barrels | Finite, nonnegative real number |
| `gas_quota`, `gas_actual` | Gas volume in Mcf | Finite, nonnegative real number |

Missing fields, `None`, strings, booleans, nonfinite values and values outside
the stated ranges do not become measured zeros. Invalid dashboard metrics
have no numeric trace and show `NOT_EVALUATED`; unavailable quota values are
blank bars with an annotation. An explicitly supplied zero remains zero.
Input mappings are not modified. An absent or invalid dashboard mapping marks
all metrics `NOT_EVALUATED`.

## Method and sources

The percentage calculation is `actual / permitted * 100`. The percentage
scale follows [NIST SP 811, section 7.10.2][nist] (online revision 2025).
The actual/permitted ratio is the existing implementation in
`ComplianceMetrics.production_compliance_percentage`, in
`packages/worldenergydata-bsee/src/worldenergydata/bsee/reports/comprehensive/templates/compliance_models.py`
at revision `d867ba1e` (2026).

The safety coefficients, score bounds and color bands are existing repository
policy, from `SafetyMetrics.calculate_safety_score` in that model file and
`get_compliance_status_color` in the adjacent `compliance_calculations.py`,
at the same revision. The dashboard retains the gauge bands, markers and
layout from `compliance_charts.py` at that revision. These values have no
independently established regulatory basis in this change; a regulatory
acceptance check is **NOT_EVALUATED**. Applicable acceptance criteria must be
provided and qualified separately.

The quota chart retains its existing gas display scale: the input in Mcf is
divided by a thousand and labelled “thousand Mcf.” Oil remains in barrels.
The two categories use different units and their bar heights should not be
compared as equivalent physical volumes.

## Worked example

Run in an environment with the repository and its reporting dependencies:

```bash
python examples/bsee_compliance_charts.py --output-dir "$TMPDIR/compliance-example"
```

All inputs below are synthetic. No operating data or regulatory limits are
assumed.

| Input | Value |
| --- | --- |
| Permitted oil production | 100000 bbl |
| Actual oil production | 110000 bbl |
| Incidents, lost time incidents and safety violations | Zero each |
| Safety inspections | 12 |
| Safety training | 1000 hours |
| Environmental and overall scores; gas quota and actual | Not supplied |

Independent hand calculation using the repository policy cited above:

- Production: `110000 / 100000 * 100 = 110.0 %`.
- Safety: start at unity, with no incident deductions. Inspection bonus is
  `min(0.1, 12 * 0.01) = 0.1`; training bonus is
  `min(0.05, 1000 * 0.001) = 0.05`. Applying the unit cap gives `1.0`.
- The dashboard displays production at `110.0 %` and safety at `100.0 %`.
  Environmental and overall scores show `NOT_EVALUATED`.
- The quota chart displays the supplied oil values and leaves the gas values
  blank, labelled `NOT_EVALUATED`.

The script writes `compliance_dashboard.html` and
`production_quota_chart.html` to the supplied folder and prints:

```json
{
  "production_compliance_pct": 110.0,
  "safety_score": 1.0,
  "not_evaluated": [
    "environmental_score",
    "overall_compliance_score",
    "gas_quota",
    "gas_actual"
  ]
}
```

## Regression coverage and limits

The calculation and visualization tests exercise all ten formerly expected
failures. The discoverable unit tests in
`tests/unit/bsee/reports/comprehensive/templates/test_compliance_charts.py`
check exact serialized chart values, unavailable inputs, explicit zero,
score bounds, palette boundaries and the template entry points.

Plotly templates legitimately include `error_x` and `error_y` schema keys.
The HTML regression therefore decodes the actual chart payload and checks its
indicator traces. Searching the entire HTML for the word “error” rejects valid
Plotly output. Browser execution and CDN availability are not tested here.
The environmental trend chart still contains its existing placeholder history;
this change does not qualify that history as measured data.

[nist]: https://www.nist.gov/pml/special-publication-811/nist-guide-si-chapter-7-rules-and-style-conventions-expressing-values#7102
