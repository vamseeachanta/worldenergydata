# Spar versus semisub calibration: evidence readiness

## Summary

Slice 1 adds an auditable evidence gate for future spar versus semisub
experiments. It does not establish a discriminator or change recommendations.
An observation is `ELIGIBLE` only when its supplied provenance meets the
pre-decision protocol. Missing information is `NOT_EVALUATED`; known outcome
proxies and co-decided or late observations are `REJECTED`.

The existing catalog does not supply the per-value publication dates and
documented concept-decision dates this protocol requires. Predictive lift is
therefore **NOT_EVALUATED**, rather than a measured negative result. The
[existing calibration figures](calibration-v2.md) remain in-sample diagnostics.

## Revision history

| Revision | Date | Change and reason |
|---|---|---|
| Initial | 2026-10-19 | Add a dated-evidence audit before testing a new hull discriminator. |

## Evidence protocol

The methodological source is
[*Leakage and the Reproducibility Crisis in ML-based Science*](https://arxiv.org/pdf/2207.07048v1),
preprint version 1, 2022, section 2.4: illegitimate features [L2] and temporal
leakage [L3.1]. The paper requires a domain argument for feature legitimacy;
chronology alone does not establish legitimacy. The
[institutional research page](https://reproducible.cs.princeton.edu/#taxonomy)
also describes these failure modes. Both were opened; the publisher PDF was
inaccessible, so the preprint is the source used here.

For a candidate observation, the local audit convention is:

`eligible = candidate AND present AND legitimate_basis_supplied AND
pre_decision AND sourced_value AND sourced_decision AND (available_on < selected_on)`

Here `available_on` is the first public availability of the **exact value and
vintage**, and `selected_on` is the earliest documented concept choice, rather
than the later production date. Sources must identify the document and location
that support each date. The strict inequality is a conservative implementation
convention derived from the source, not a published hull-selection threshold.
Same-day evidence is rejected because calendar dates cannot establish order.
No hull coefficient, depth cutoff, accuracy floor or engineering limit is added.

The caller must classify timing and supply an explanation of independence from
the host choice. A retrospective article describing a reservoir does not by
itself show that its particular estimate was publicly available before selection.
The audit checks supplied metadata, without fetching or verifying documents.
An `ELIGIBLE` result is neither evidence of causal independence nor permission
to use a feature without scientific review.

## Candidate coverage

The research questions follow #640 and the existing
[concept-selection briefing](concept-selection-and-ai-cad-briefing.md), sections
A2 and A3. They are hypotheses, not accepted predictors:

| Candidate input | Required evidence beyond its value |
|---|---|
| `reservoir_compactness`, `drill_centre_spread` | Dated appraisal geometry independent of the selected layout |
| `intervention_frequency`, `expected_well_count` | Dated pre-decision expectations, rather than built well counts |
| `hpht` | Dated appraisal finding and its definition |
| `prior_spar_count`, `prior_semisub_count` | History restricted to developments already known before this decision |
| `predecision_reserves_mmboe` | The contemporaneous estimate, rather than a revised modern estimate |
| `seabed_terrain` | Dated site evidence independent of the selected mooring pattern |

[*Assessing floating platform concepts for deepwater production*](https://www.offshore-mag.com/field-development/article/16761414/assessing-floating-platform-concepts-for-deepwater-production),
2013, sections on reservoir characteristics, platform functions and well access,
was opened. It relates reservoir geometry to well access and tree decisions,
and discusses flexibility and execution constraints. It does not establish a
validated spar versus semisub predictor for this catalog. No numerical screening
rule is taken from it.

The gate explicitly rejects `concept_type`, tree and riser types, raw built
well/tree/manifold counts, layout and equipment choices, hull dimensions,
mooring pattern and installation method even if they are backdated or declared
pre-decision. Unknown feature names remain `NOT_EVALUATED`. Decision era and
design replication need a separately reviewed representation before admission;
they are not inferred from first production or free-text facility descriptions.

## Use and missing data

The research API is in `worldenergydata.field_development.calibration_evidence`.
It accepts `DecisionEvidence` and `FeatureEvidence` records. `audit_feature`
checks one observation; `audit_candidates` reports every registered candidate,
retains extra supplied observations and refuses duplicate feature names.
True zero and false values are observations; absent, blank and non-finite
values are not. It does not mutate inputs or call the recommendation engine.

```python
from worldenergydata.field_development.calibration_evidence import (
    DecisionEvidence,
    audit_candidates,
)

# The catalog has no dated per-value evidence to submit to this audit.
checks = audit_candidates([], DecisionEvidence(selected_on=None, source=None))
# Every candidate has status NOT_EVALUATED, with its missing-evidence reason.
```

`subseaiq.load_subseaiq_fields` fills `year_first_oil` and a catalog-level
`data_source`, not feature-level availability or earliest selection dates.
`host_enrichment.enrich_concepts` supplies reserves and well counts without
their publication vintages. Neither first production nor the catalog snapshot
date can substitute for those missing dates. No automatic adapter claims that
these records meet this protocol.

## Verification and later slices

The truth-table tests in `test_calibration_evidence.py` use synthetic evidence.
Their docstring writes out the date ordering used as the independent expected
result. They cover missing provenance, same-day and later publications,
outcome proxies despite backdating, unknown features, zero and false values,
duplicate observations and batch completeness. They make no empirical
classification-accuracy claim.

Slice 2 remains a forward-in-time experiment: obtain dated public observations,
choose the overlap cohort before evaluating, derive all transformations and
history features from training data only, and compare against era/history
baselines. Report sample counts, confusion and uncertainty without treating
the existing tuned bands as a held-out result. The leakage paper, section 2.4
[L1/L3.1], supplies the separation principle; no experiment has been run here.

Slice 3 remains conditional on evidence: change scoring only if an independent
comparison supports improvement in the target pair without regressing other
concepts, as required by #640. No statistical acceptance threshold is invented.
No feature is admitted automatically from an as-built record. The issue remains
open because readiness and discrimination are different questions.
