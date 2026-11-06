# Intervention HSE intake

This module extracts the reusable classifier input from the Phase 1A inventory.
It does not infer intervention involvement from a taxonomy activity code.

```python
from worldenergydata.bsee.analysis.intervention_hse import (
    load_hse_incidents,
    classify_incidents,
    count_activity_patterns,
)
from worldenergydata.safety_analysis.taxonomy.incident_classifier import IncidentClassifier

# Verify the source and select the intervention cohort before classification.
rows = load_hse_incidents(database_path)
classified = classify_incidents(verified_cohort, source=verified_source,
                                classifier=IncidentClassifier())
cells = count_activity_patterns(classified)
```

The loader requires `id`, `description`, and `incident_type` columns in
`hse_incidents`; it preserves `accident_type` separately when present. Missing
databases, incompatible schemas, and absent or duplicate IDs raise exceptions.
A valid empty table returns an empty tuple. The database is opened read-only.
Operator and lease fields are excluded. Descriptions and record-level
classifications are internal inputs, not public report material.

Classification and counting require the `worldenergydata-safety_analysis`
distribution, included by the repository's root distribution. The loader alone
uses the standard library. Classifier confidence remains an upstream matching
heuristic; no measured-accuracy claim is established by these functions.

Counts use taxonomy codes only and omit cells smaller than five records,
following the 2026 issue-416 plan's Operator Aggregation Contract, rule 2.
Suppressed labels and population totals are omitted. Overlapping releases
require separate disclosure assessment. These descriptive counts have no
exposure denominator and do not establish incident rates or causal patterns.

WAR/fleet loading, source verification, operator/lease/date joins, recommendations,
`generate_memo`, HTML output, historical memo byte equivalence, and population
confidence regression remain outside this initial extraction. No exposure-based
or statistical acceptance check is evaluated here.

Sources:

- `scripts/exploration/intervention_hse_phase1a_explore.py` (2026),
  `hse_incidents_profile`: input schema and SQL category counts.
- `docs/plans/2026-05-18-issue-416-intervention-hse-patterns.md` (2026),
  Operator Aggregation Contract, rule 2: minimum cell size.
- `safety_analysis/taxonomy/activity_definitions.py` and
  `incident_classifier.py`: existing mappings and heuristic scores.
- [SQLite URI filenames, sections 3.1 and 3.3](https://www.sqlite.org/uri.html):
  URI escaping and read-only mode.
