# Legacy importer follow-up drafts

These numbered specifications support the open-item register in [agent-pack.md](agent-pack.md), revision 1, at code revision `01e65a40ab2f0aa06e663f26b70a94a186efa191`. They are unfiled drafts; no issue number or implementation is claimed. Responsibility rests with the maintainer.

## Draft 1: Decide the physical legacy importer disposition

O1 / U3: compare legacy schemas and acquisition routes with the current package and compatibility redirects. Choose retention with direct physical-source and persistence tests, or deletion with callers and stale documentation reconciled. Acceptance requires an explicit disposition of all four physical files; redirected tests alone do not demonstrate their execution.

## Draft 2: Detect silent parse, missing-value and completeness failures

O2: cover SF01–SF29 with detection tests or an explicit retirement under Draft 1. In particular, exercise a CSV containing `NA`, `N/A`, `null` and blank cells across all seven numeric fields and identifier, operator and severity fields. Assert explicit None values or rejection for missing cells, integer counts for valid cells, and rejected-input counts. Cover malformed numeric/date text, non-string values, missing defaults and empty processor results. Acceptance requires each retained failure path to have a detection check, and invalid input to remain distinguishable from missing input.

## Draft 3: Qualify the source data and independent reference fixture

O3 / U1 / U2: establish source vintage, endpoint availability, payload schema, raw units and date/time conventions under the source-acceptance contract in #462. Add an independently qualified end-to-end fixture and expected results with stated tolerances. Acceptance requires traceable input provenance and a data-to-database comparison; mocked adapter tests and fixture arithmetic do not qualify the source.

## Draft 4: Index retained implementation families

O4: reconcile current and legacy implementations and add owning-repository map entries for CSV ingestion, reporting-date/count normalization and the incident, penalty and statistics ZIP acquisition families. Resolve routing maturity using an existing registry, if available. Acceptance requires traceable family ownership and a duplicate disposition; do not invent registry entries merely to fill a gap.

## Draft 5: Complete ownership and independent clearance records

O5 / U4: assign a deputy quality manager, record shared-log references and obtain independent review. File these drafts and replace pending markers with issue numbers before clearance. Acceptance requires an assigned deputy, traceable follow-ups and review at the current revision; this draft confers no clearance.
