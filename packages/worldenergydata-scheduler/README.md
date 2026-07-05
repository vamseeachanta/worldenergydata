# worldenergydata-scheduler

`scheduler` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

The top-level data-refresh orchestrator: scheduled refresh jobs, staleness
monitoring, alerting, and Parquet output across the carved source domains. Its
per-source refresh jobs import the source-domain members
(brazil_anp, bsee/hse, eia, metocean, sodir, spain, ukcs), so this
member depends on each of them — but no carved domain imports the scheduler
back, so there is no dependency cycle.

Importable transparently as `worldenergydata.scheduler` once the workspace is
installed (`uv sync --all-extras`).

## Spain CORES refresh

`spain_cores_refresh` downloads the official CORES oil and gas workbooks into
`data/spain/cores`, writes normalized CORES production CSV files, and refreshes
the small committed Ayoluengo fixture when `refresh_fixture: true` is configured.
The Spain source package is imported lazily only when the job runs, keeping CLI
startup/help paths free of live-source imports.
