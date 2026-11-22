# Original and modified-shape pipeline pressure screening

The original criterion and the retained modified-shape screening variant give different burst pressures. Both require measured geometry, material strength and operating pressure. This example uses synthetic inputs and demonstrates the equations; it does not qualify a pipeline for service.

## Revision history

| Revision | Date | What changed and why |
| --- | --- | --- |
| 0 | 2026-10-22 | Added independent hand calculations and disclosed the historical modified flow-stress choice to resolve #1295. |

## Source and scope

[Review of Methods for Determining the Strength of Corroded Natural Gas Pipelines Based on Actual Remaining Wall Thickness, ORNL/TM-2019/1192, May 2019](https://www.osti.gov/servlets/purl/1855701), sections 2.1–2.4, supplies the equations used here. Its original-criterion reference is ASME B31G-1991 (reaffirmed 2004). The licensed standard itself was not accessed, and no comparison against its 2012 edition is claimed.

The scope is blunt part-wall corrosion in ductile line pipe under internal pressure. Toughness, interacting defects, temperature, weld/crack applicability and field measurements need separate qualification. Depth beyond 80% is outside the implemented pressure criterion and raises; the limit comes from sections 2.1.1–2.1.2 of the public report.

## Inputs and method

Synthetic inputs: outside diameter D = 200.0 mm, wall thickness t = 10.0 mm, SMYS = 400.0 MPa, depth d/t = 0.5 and MAOP = 10.0 MPa. Two lengths are defined exactly as L = sqrt(z D t) for z = 10.0 and 40.0; the table displays their lengths rounded. The displayed safe pressures use the report's example factor 1.39 (section 2.4.1, p. 10), which needs application-specific qualification.

The following coefficients are from the cited public report, rather than recalled values:

- Original flow stress S = 1.1 SMYS (section 2.2.1). For z ≤ 20, M = sqrt(1 + 0.8 z), a = (2/3)(d/t), and Pf = (2t/D) S (1-a)/(1-a/M) (equations 2, 5 and 8). For z > 20, Pf = (2t/D) S (1-d/t) (equation 6).
- Modified shape: a = 0.85 d/t (section 2.1.2). M = sqrt(1 + 0.6275 z - 0.003375 z²) for z ≤ 50, otherwise M = 0.032 z + 3.3 (equations 10–11). The burst-pressure relationship is equation 2.
- The retained implementation uses S = 0.9 SMYS, documented as a historical choice in knowledge-pack revision 1, section 6 SF2. This is a compatibility variant, **not the published modified criterion**: section 2.2.2 specifies SMYS + 10,000 psi. The current output explicitly states the difference; this example does not introduce a unit conversion or silently substitute the published flow stress.

Original hand calculation: the pressure base is (2 × 10 / 200) × 1.1 × 400 = 44.0 MPa and the short-flaw area is 1/3. At z = 10, M = 3.0, so Pf = 44 × (2/3)/(1-1/9) = 33.0 MPa. At z = 40, the long-flaw rule gives Pf = 44 × 0.5 = 22.0 MPa.

Modified-variant hand calculation: the base is (2 × 10 / 200) × 0.9 × 400 = 36.0 MPa and a = 0.425. Thus Pf = 20.7/(1-0.425/M), with M from equation 10 for both lengths. Division by the example factor gives the safe-pressure column below.

| z | Length (mm) | Original Pf (MPa) | Variant Pf (MPa) | Original safe (MPa) | Variant safe (MPa) |
| --- | --- | --- | --- | --- | --- |
| 10.0 | 141.4 | 33.0 | 24.7 | 23.7 | 17.8 |
| 40.0 | 282.8 | 22.0 | 22.8 | 15.8 | 16.4 |

At these synthetic pressures both variants clear MAOP. An `accept` label means only that the implemented pressure screen clears the supplied MAOP; it does not establish code compliance or a monitoring interval. No sourced monitoring threshold or measured corrosion-growth rate is available, so the former depth-based `monitor` default is removed and remaining life is unknown.

## Review-ratio check and regression evidence

The reviewed old `b31g` branch used SMYS and the modified M. At d/t = 0.5 its ratio to the sourced original long-flaw result is [(2/3)/(1-1/(3M))]/(1.1 × 0.5). Evaluating M from equations 10–11 gives overstatements of 30.8% at z = 40 and 27.8% at z = 100, confirming the review's rounded ratios. These ratios are independent of the common diameter, wall and strength pressure base.

`tests/unit/pipeline_safety/test_criteria.py::test_original_hand_calculation`, `tests/unit/pipeline_safety/test_criteria.py::test_modified_variant_hand_calculation` and `tests/unit/pipeline_safety/test_criteria.py::test_review_ratios_against_confirmed_original` implement these independent calculations. They also test both piecewise boundaries. Expected values are derived in their docstrings; the implementation is never called to construct an expected pressure.

The shipped CSV and standalone synthetic demonstration use 80% for their deepest defect instead of the former out-of-scope depths. The registry's expected minimum safe pressure has its own written hand calculation. `tests/unit/pipeline_safety/test_import_integrity.py::test_registered_example_bundle` checks the resulting CSV, summary and narrative.
