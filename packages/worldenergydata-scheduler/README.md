# worldenergydata-scheduler

`scheduler` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, batch 5 final tail, #529).

The top-level data-refresh orchestrator: scheduled refresh jobs, staleness
monitoring, alerting, and Parquet output across the carved source domains. Its
per-source refresh jobs import the source-domain members
(brazil_anp, bsee/hse, eia, metocean, sodir, ukcs), so this
member depends on each of them — but no carved domain imports the scheduler
back, so there is no dependency cycle.

Importable transparently as `worldenergydata.scheduler` once the workspace is
installed (`uv sync --all-extras`).
