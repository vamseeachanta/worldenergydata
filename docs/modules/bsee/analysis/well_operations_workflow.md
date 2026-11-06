# Local well-operations snapshot analysis

The `worldenergydata.bsee.analysis.intervention.insight_workflow` module produces
aggregate findings from one explicitly selected, reviewed enriched WAR CSV.
It reuses `ComprehensiveActivityAnalyzer` record counting. It does not download,
refresh, enrich, join, publish, or discover inputs.

Run in an environment with the BSEE workspace package installed:

```bash
python -m worldenergydata.bsee.analysis.intervention.insight_workflow \
  --input "$WAR_CSV" --source "$SOURCE_JSON" --output "$NEW_OUTPUT_DIRECTORY" \
  --code-ref "$CODE_COMMIT" --catalog-ref "$CATALOG_SHA256"
```

`CODE_COMMIT` is the Git SHA-1 of the executing code; `CATALOG_SHA256` identifies
the inspected catalog bytes. Neither is inferred from the current directory.
The output directory must be new. Inputs are read without modification. A failed
write may leave an incomplete directory; inspect it and select a fresh output
directory for a retry. No automatic deletion or overwrite is performed.

The source JSON is an evidence object with these required fields:

| Field | Required evidence |
| --- | --- |
| `dataset_id`, `version` | Existing dataset identity/version as opaque alphanumeric, underscore or hyphen slugs |
| `source_url` | Public HTTPS BSEE citation, without credentials, query or fragment |
| `source_class` | `public-federal` |
| `license` | `public-domain`, established by source review |
| `review_state` | `reviewed` |
| `readiness` | `ready`, established by the source-readiness probe |
| `data_as_of` | Source vintage as an ISO calendar date |
| `retrieved_at` | ISO timestamp with timezone, on or after source vintage |
| `sha256` | SHA-256 of the exact input CSV bytes |
| `derivation` | `reviewed-enriched-war`, attesting that enrichment lineage was checked |

These assertions are supplied by the caller. Schema checks and matching hashes
do not authenticate review, source rights, freshness, catalog membership or
lineage. Do not use synthetic fixtures as federal evidence. Publication remains
blocked pending bundle review even when all input checks pass. Arbitrary extra
metadata and raw records are excluded from the output projection. Source
metadata itself must be reviewed for public suitability.

`ACTIVITY_CATEGORY` is required. Exact `drilling` and `intervention` labels are
counted; all other labels and missing categories are counted as other. Empty
snapshots are rejected. Optional `YEAR` labels give annual counts; missing or
invalid years remain in an undated bucket. Supplied year labels are not validated
against operation dates. Each row counts once, including duplicate source rows;
counts are not unique wells, operating days, exposure or incident rates.

The counting equations are indicator sums: drilling records equal the number of
rows labelled drilling, intervention records equal the number labelled
intervention, and other records equal total minus those two counts. The method
is the existing `ComprehensiveActivityAnalyzer._analyze_cross_activity`; no
engineering coefficient, empirical threshold or acceptance limit is introduced.
The source portal is [BSEE Raw Data](https://www.data.bsee.gov/Main/RawData.aspx),
eWell Submissions WAR. Its raw exports require a separately reviewed enrichment
step before this workflow can consume them.

Outputs are `insights.json`, `findings.html`, and `manifest.json`. The manifest
records input provenance, code/catalog digests, output SHA-256 values, and links
to upstream contract/readiness issues. Written bytes are read back. The manifest
is a local bundle index, not the upstream workflow-run schema. The HTML includes
findings, revision history, annual counts, limitations, and next probes.

Production, FDAS, HSE, duration and population coverage are `NOT_EVALUATED`.
No operator-level findings or HSE cross-tabs are emitted. Raw-WAR enrichment,
authenticated provenance, upstream YAML run manifests and JSONL attempt history,
wiki routing, and production/FDAS/HSE joins remain follow-up integration work in
[the workflow issue](https://github.com/vamseeachanta/worldenergydata/issues/452).
The upstream dependencies remain
[the manifest contract](https://github.com/vamseeachanta/worldenergydata/issues/450)
and [source readiness](https://github.com/vamseeachanta/worldenergydata/issues/451).
