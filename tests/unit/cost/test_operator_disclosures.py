"""Annual disclosure foundation contracts from issue #334 (2026).

All uncited amounts and dates below are synthetic validation inputs. They
represent no operator or development. Expected values follow the explicit
input literals and the issue's scope/provenance rules, without conversion.
"""

from decimal import Decimal
from pathlib import Path
from runpy import run_path

import pytest
from pydantic import ValidationError

from worldenergydata.cost.data_collection import (
    OperatorDisclosureRecord,
    ScopeType,
    load_operator_disclosures_dataset,
)
from worldenergydata.cost.data_collection.linkage import (
    LinkageStatus,
    disclosure_row_is_linkable,
    resolve_cost_datapoint_link,
)
from worldenergydata.cost.data_collection.public_dataset import load_public_dataset


@pytest.fixture
def row():
    """Synthetic complete input; the reported amount is exactly 12.30 million."""
    return {
        "operator": "Synthetic operator",
        "fiscal_year": 2023,
        "scope": "project",
        "project_name": "Synthetic development",
        "filing_type": "annual_report",
        "metric_name_normalized": "project_total_capex_reported",
        "metric_name_reported": "Total estimated investment",
        "amount": "12.30",
        "currency": "NOK",
        "unit": "million",
        "value_basis": "Gross estimate, nominal money",
        "source_title": "Synthetic annual report 2023",
        "source_url": "https://example.org/annual-report.pdf",
        "page_reference": "p. 7, investment table",
        "quoted_text": "Total estimated investment NOK 12.30 million",
        "confidence": "high",
        "source_priority": "operator_annual_report",
    }


@pytest.mark.parametrize(
    "field",
    [
        "operator",
        "fiscal_year",
        "scope",
        "filing_type",
        "amount",
        "currency",
        "unit",
        "value_basis",
        "metric_name_normalized",
        "metric_name_reported",
        "source_title",
        "source_url",
        "page_reference",
        "quoted_text",
        "confidence",
        "source_priority",
    ],
)
def test_missing_required_field_is_rejected(row, field):
    row.pop(field)
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


@pytest.mark.parametrize(
    "field",
    [
        "operator",
        "project_name",
        "metric_name_reported",
        "value_basis",
        "source_title",
        "page_reference",
        "quoted_text",
    ],
)
def test_blank_text_is_rejected(row, field):
    row[field] = "  "
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


@pytest.mark.parametrize(
    "url",
    ["https://", "https:///report", "file:report", "https://example.org/a b"],
)
def test_malformed_source_url_is_rejected(row, url):
    row["source_url"] = url
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


@pytest.mark.parametrize("amount", ["NaN", "Infinity", "-Infinity", True])
def test_invalid_monetary_value_is_rejected(row, amount):
    row["amount"] = amount
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


def test_as_reported_amount_and_label_are_preserved(row):
    """Hand check: identity transcription of '12.30' retains its trailing zero."""
    record = OperatorDisclosureRecord(**row)
    assert record.amount == Decimal("12.30")
    assert str(record.amount) == "12.30"
    assert record.currency == "NOK"
    assert record.unit == "million"
    assert record.metric_name_reported == row["metric_name_reported"]
    assert record.model_dump(mode="json")["amount"] == "12.30"


@pytest.mark.parametrize("project_name", [None, "", " "])
def test_project_scope_requires_name(row, project_name):
    row["project_name"] = project_name
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


def test_operator_scope_forbids_project_name_and_project_metric(row):
    row["scope"] = "operator"
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)
    row.pop("project_name")
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)
    row["metric_name_normalized"] = "operator_capex_reported"
    record = OperatorDisclosureRecord(**row)
    assert record.scope == ScopeType.OPERATOR
    assert record.project_name is None
    assert not disclosure_row_is_linkable(record.scope.value)


def test_project_scope_forbids_operator_metric(row):
    row["metric_name_normalized"] = "operator_capex_reported"
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


@pytest.mark.parametrize(
    "field", ["restated", "version", "cost_datapoint_id", "metric_value"]
)
def test_out_of_scope_fields_are_rejected(row, field):
    row[field] = "unsupported"
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


@pytest.mark.parametrize(
    "field,value", [("currency", "usd"), ("unit", "barrels"), ("fiscal_year", True)]
)
def test_invalid_money_context_or_year_is_rejected(row, field, value):
    row[field] = value
    with pytest.raises(ValidationError):
        OperatorDisclosureRecord(**row)


def test_unmatched_project_remains_valid(row):
    record = OperatorDisclosureRecord(**row)
    assert disclosure_row_is_linkable(record.scope.value)
    result = resolve_cost_datapoint_link(record.operator, record.project_name)
    assert result.status == LinkageStatus.UNLINKED
    assert "cost_datapoint_id" not in OperatorDisclosureRecord.model_fields


def test_exact_linkage_is_derived_and_case_sensitive(row):
    sanction = load_public_dataset()[0]
    row.update(operator=sanction.operator, project_name=sanction.project_name)
    record = OperatorDisclosureRecord(**row)
    result = resolve_cost_datapoint_link(
        record.operator, record.project_name, [sanction]
    )
    assert result.status == LinkageStatus.LINKED
    assert (
        resolve_cost_datapoint_link(
            record.operator.swapcase(), record.project_name, [sanction]
        ).status
        == LinkageStatus.UNLINKED
    )


def test_seed_has_both_multiyear_series_and_complete_provenance():
    """Issue #334 plan (2026), TDD table: capped seed, both scopes and years."""
    records = load_operator_disclosures_dataset()
    # Seed cap comes from the issue #334 plan, Acceptance Criteria (2026).
    assert 0 < len(records) <= 12
    for scope in ScopeType:
        groups = {}
        for record in records:
            if record.scope == scope:
                key = (
                    record.operator,
                    record.project_name,
                    record.metric_name_normalized,
                )
                groups.setdefault(key, set()).add(record.fiscal_year)
        assert any(len(years) > 1 for years in groups.values())
    for record in records:
        assert record.source_url.startswith("https://")
        assert all((record.source_title, record.page_reference, record.quoted_text))
        assert str(record.fiscal_year) in record.source_title
        assert record.amount.is_finite()


def test_loader_returns_independent_lists_and_records():
    first = load_operator_disclosures_dataset()
    second = load_operator_disclosures_dataset()
    assert first == second
    assert first is not second
    assert first[0] is not second[0]
    first.clear()
    assert load_operator_disclosures_dataset() == second


def test_seed_is_exact_current_year_transcription_without_imputation():
    """Independent table transcription, not values derived by the loader.

    Aker BP Annual Report 2022: p. 17 (PDF p. 18) investment paragraph
    gives approximately NOK 16 billion real; p. 117 (PDF p. 118), APM
    CAPEX table, Group 2022 column gives USD 1 626 987 thousand.
    Annual Report 2023: p. 12 repeats approximately NOK 16 billion real;
    p. 193, APM CAPEX table, Group 2023 column gives USD 3 267.3 million.
    The expected four observations are these four cells/paragraphs only.
    Comparative columns and missing years add zero observations.
    """
    records = load_operator_disclosures_dataset()
    assert [
        (r.scope.value, r.fiscal_year, str(r.amount), r.currency, r.unit)
        for r in records
    ] == [
        ("project", 2022, "16", "NOK", "billion"),
        ("project", 2023, "16", "NOK", "billion"),
        ("operator", 2022, "1626987", "USD", "thousand"),
        ("operator", 2023, "3267.3", "USD", "million"),
    ]
    # Each fiscal year uses its own report, not a later report's comparative.
    assert all(f"annual-report-{r.fiscal_year}.pdf" in r.source_url for r in records)
    assert all(
        "real terms" in r.value_basis for r in records if r.scope == ScopeType.PROJECT
    )


@pytest.mark.parametrize("amount", ["0", "-12.30"])
def test_signed_or_zero_as_reported_money_is_valid(row, amount):
    """Synthetic accounting signs are preserved, not absolutized or imputed."""
    row["amount"] = amount
    assert OperatorDisclosureRecord(**row).amount == Decimal(amount)


def test_records_are_immutable(row):
    record = OperatorDisclosureRecord(**row)
    with pytest.raises(ValidationError):
        record.amount = Decimal(0)


def test_worked_example(capsys):
    """The four transcribed source observations above give these literal lines."""
    example = (
        Path(__file__).resolve().parents[3]
        / "examples"
        / "workflows"
        / "annual-cost-disclosures"
        / "example.py"
    )
    run_path(str(example), run_name="__main__")
    assert capsys.readouterr().out.splitlines() == [
        "scope | fiscal year | reported metric | as-reported amount",
        "project | 2022 | total investments | 16 NOK billion",
        "project | 2023 | total investments | 16 NOK billion",
        "operator | 2022 | CAPEX | 1626987 USD thousand",
        "operator | 2023 | CAPEX | 3267.3 USD million",
        "project linkage: unlinked",
        "project linkage: unlinked",
        "operator linkage: ineligible",
        "operator linkage: ineligible",
    ]
