# worldenergydata-ukcs

`ukcs` domain of the **worldenergydata** namespace, carved out as a uv
workspace member (ADR 0001 Phase 2 — domain-package split, #529).

Importable transparently as `worldenergydata.ukcs` once the workspace is
installed (`uv sync --all-extras`). Depends on `worldenergydata-core` for the
shared `worldenergydata.common` layer.

Production-component field coverage, unknown-value handling, attribution and
limits are documented in [UKCS production-component extraction](../../docs/ukcs-production-components.html).
The offline [worked example](../../examples/ukcs/production_components.py) shows
synthetic inputs, the conversion method and monthly/annual answers.
