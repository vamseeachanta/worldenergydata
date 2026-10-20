"""Synthetic annual-disclosure lineage example, not production filing evidence.

Contract source: the issue 344 plan dated 2026-04-23, Scope Boundaries.
Hand calculation from the declared inputs: 2023 is restated from 100 to 120
USD million; 2024 is 150 USD million. Current delta = 150 - 120 = 30;
current delta ratio = 30 / 120 = 0.25. No currency conversion is performed.
"""

import json

from worldenergydata.cost.data_collection import ingest_disclosure_rows
from worldenergydata.cost.disclosure_analytics import (
    DisclosureRecord,
    load_current_effective_disclosure_rows,
    load_disclosure_revision_history,
    load_project_cost_revision_view,
)


def _synthetic_inputs() -> list[dict]:
    base = {
        "operator": "operator",
        "project_name": "asset",
        "fiscal_year": 2023,
        "scope_type": "project",
        "normalized_metric_name": "capex",
        "metric_unit": "USD_MM",
        "citation": {
            "source_title": "Synthetic worked example; not a real filing",
            "source_url": "https://example.org/synthetic-disclosure",
            "page_reference": "Declared inputs in this example",
            "quoted_text": "Synthetic input; no production evidence.",
            "confidence": "low",
            "source_priority": "operator_annual_report",
        },
    }
    original = {
        **base,
        "metric_value": 100.0,
        "revision": {
            "logical_disclosure_key": "capex-2023",
            "version_id": "original",
            "revision_classification": "original",
        },
    }
    restated = {
        **base,
        "metric_value": 120.0,
        "revision": {
            "logical_disclosure_key": "capex-2023",
            "version_id": "restated",
            "revision_classification": "restated",
            "supersedes_version_id": "original",
            "publication_date": "2024-04-01",
            "revision_reason": "Synthetic correction to the reported amount",
        },
    }
    following = {
        **base,
        "fiscal_year": 2024,
        "metric_value": 150.0,
        "revision": {
            "logical_disclosure_key": "capex-2024",
            "version_id": "following",
            "revision_classification": "original",
        },
    }
    return [original, restated, following]


def worked_example() -> dict:
    """Validate and retain evidence, then project explicitly to USD-million capex."""
    result = ingest_disclosure_rows(raw_rows=_synthetic_inputs())
    if result.invalid or result.conflicts or result.duplicates:
        raise ValueError("synthetic example did not ingest as distinct evidence")
    rows = [item.row for item in result.accepted]
    history = load_disclosure_revision_history(rows)
    current = load_current_effective_disclosure_rows(rows)
    # The input declares capex in USD_MM; other units require a separate adapter.
    projected = [
        DisclosureRecord(
            operator=row.operator,
            project_name=row.project_name,
            fiscal_year=row.fiscal_year,
            reported_capex_usd_mm=row.metric_value,
            scope=row.scope_type.value,
            currency="USD",
            revision=row.revision,
            provenance=row.citation.model_dump(mode="json"),
        )
        for row in rows
    ]
    series = load_project_cost_revision_view(projected)
    return {
        "history_values_usd_mm": [r.metric_value for r in history],
        "current_values_usd_mm": [r.metric_value for r in current],
        "selected_classifications": [
            r.revision.revision_classification for r in series
        ],
        "latest_delta_usd_mm": series[-1].yoy_delta_usd_mm,
        "latest_delta_ratio": series[-1].yoy_delta_pct,
    }


if __name__ == "__main__":
    print(json.dumps(worked_example(), indent=2))
