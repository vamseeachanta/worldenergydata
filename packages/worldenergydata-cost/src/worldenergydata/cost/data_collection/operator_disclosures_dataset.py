"""Minimal current-year annual disclosures; no downloads or imputed records.

Each amount is transcribed from the cited operator report and column. The
development series is a disclosed bundle, not either constituent development.
Comparative prior-year columns (including restated columns) are never used.
"""

from __future__ import annotations

from worldenergydata.cost.data_collection.operator_disclosures_schema import (
    OperatorDisclosureRecord,
)

_REPORT_2022 = (
    "https://akerbp.com/wp-content/uploads/2023/03/aker-bp-annual-report-2022.pdf"
)
_REPORT_2023 = (
    "https://akerbp.com/wp-content/uploads/2024/03/aker-bp-annual-report-2023.pdf"
)


def load_operator_disclosures_dataset() -> list[OperatorDisclosureRecord]:
    """Return fresh validated as-reported rows, without normalization or linkage.

    The four-row sample is intentionally below the issue #334 plan's seed
    cap. Every observation comes from its own fiscal-year report. Primary
    source transcription earns high confidence; it does not establish that
    gross real investment estimates and consolidated capex are comparable.
    """
    common = {
        "operator": "Aker BP",
        "filing_type": "annual_report",
        "confidence": "high",
        "source_priority": "operator_annual_report",
    }
    project = {
        "scope": "project",
        "project_name": "Reported two-tieback development bundle",
        "metric_name_normalized": "project_total_capex_reported",
        "metric_name_reported": "total investments",
        "currency": "NOK",
        "unit": "billion",
        "value_basis": (
            "Approximate gross total investment in real terms for the two "
            "subsea tiebacks; no base-price year stated. Not annual expenditure."
        ),
    }
    operator = {
        "scope": "operator",
        "metric_name_normalized": "operator_capex_reported",
        "metric_name_reported": "CAPEX",
        "currency": "USD",
        "value_basis": (
            "Group annual CAPEX: fixed-asset disbursements excluding capitalised "
            "interest plus investment-related lease payments; as reported."
        ),
    }
    return [
        OperatorDisclosureRecord(
            **common,
            **project,
            # Annual Report 2022, p. 17 (PDF p. 18), two-tieback investment paragraph.
            fiscal_year=2022,
            amount="16",
            source_url=_REPORT_2022,
            source_title="Aker BP Annual Report 2022",
            page_reference="p. 17 (PDF p. 18), two-tieback investment paragraph",
            quoted_text=(
                "The total investments are estimated to approximately "
                "NOK 16 billion in real terms."
            ),
        ),
        OperatorDisclosureRecord(
            **common,
            **project,
            # Annual Report 2023, p. 12, two-tieback investment paragraph.
            fiscal_year=2023,
            amount="16",
            source_url=_REPORT_2023,
            source_title="Aker BP Annual Report 2023",
            page_reference="p. 12, two-tieback investment paragraph",
            quoted_text=(
                "total investments are estimated to approximately "
                "NOK 16 billion in real terms."
            ),
        ),
        OperatorDisclosureRecord(
            **common,
            **operator,
            # Annual Report 2022, p. 117 (PDF p. 118), CAPEX, Group 2022 (USD 1 000).
            fiscal_year=2022,
            amount="1626987",
            unit="thousand",
            source_url=_REPORT_2022,
            source_title="Aker BP Annual Report 2022",
            page_reference="p. 117 (PDF p. 118), APM table, CAPEX, Group 2022",
            quoted_text="CAPEX 1 626 987",
        ),
        OperatorDisclosureRecord(
            **common,
            **operator,
            # Annual Report 2023, p. 193, CAPEX, Group 2023 (USD million).
            fiscal_year=2023,
            amount="3267.3",
            unit="million",
            source_url=_REPORT_2023,
            source_title="Aker BP Annual Report 2023",
            page_reference="p. 193, APM table, CAPEX, Group 2023 (USD million)",
            quoted_text="CAPEX 3 267.3",
        ),
    ]
