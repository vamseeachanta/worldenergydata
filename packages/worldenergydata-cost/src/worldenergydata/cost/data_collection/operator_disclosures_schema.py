"""Typed, as-reported annual monetary records (issue #334, 2026).

This foundation deliberately excludes restatement/version fields, monetary
conversion and stored sanction-record references. It does not replace the
generic ingestion contract or the downstream analytics record types.
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import Field, field_validator, model_validator

from worldenergydata.cost.data_collection.disclosure_ingest_contract import (
    DisclosureCitation,
)
from worldenergydata.cost.data_collection.operator_statement_registry import (
    validate_url,
)


class ScopeType(str, Enum):
    """Issue #334's explicit separation of company and development records."""

    OPERATOR = "operator"
    PROJECT = "project"


class FilingType(str, Enum):
    """Primary disclosure channels identified in the issue #334 plan (2026)."""

    ANNUAL_REPORT = "annual_report"
    TEN_K = "ten_k"
    TWENTY_F = "twenty_f"
    INVESTOR_PRESENTATION = "investor_presentation"
    REGULATOR_PDO = "regulator_pdo"
    REGULATOR_FDP = "regulator_fdp"
    PRESS_RELEASE = "press_release"


class NormalizedMetricName(str, Enum):
    """Semantic labels only; amounts and reported metric wording stay intact."""

    OPERATOR_CAPEX_REPORTED = "operator_capex_reported"
    OPERATOR_UPSTREAM_CAPEX_REPORTED = "operator_upstream_capex_reported"
    PROJECT_TOTAL_CAPEX_REPORTED = "project_total_capex_reported"
    PROJECT_REMAINING_CAPEX_REPORTED = "project_remaining_capex_reported"


class OperatorDisclosureRecord(DisclosureCitation):
    """One fiscal year's monetary disclosure with mandatory row-level evidence.

    ``amount`` is the signed printed number, stored as a finite decimal;
    ``unit`` is its printed magnitude. No multiplication or currency exchange
    takes place. ``value_basis`` preserves ownership and price-basis context
    (for example gross real investment versus consolidated annual outlays).
    Confidence describes transcription evidence, not comparability.

    The inherited citation contract is frozen and forbids unknown fields.
    Scope/metric compatibility and project-name rules implement issue #334's
    acceptance criteria; they are structural rules, not engineering limits.
    """

    operator: str = Field(min_length=1)
    fiscal_year: int = Field(strict=True, gt=0)  # Positive fiscal-year label, #334.
    scope: ScopeType
    filing_type: FilingType
    metric_name_normalized: NormalizedMetricName
    metric_name_reported: str = Field(min_length=1)
    amount: Decimal = Field(allow_inf_nan=False)
    currency: str = Field(min_length=1)
    unit: Literal["units", "thousand", "million", "billion"]
    value_basis: str = Field(min_length=1)
    project_name: str | None = None

    @field_validator("operator", "metric_name_reported", "value_basis", "project_name")
    @classmethod
    def require_nonblank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("must be a non-blank string")
        return value

    @field_validator("source_url")
    @classmethod
    def require_valid_source_url(cls, value: str) -> str:
        return validate_url(value)

    @field_validator("currency")
    @classmethod
    def require_currency_code(cls, value: str) -> str:
        if not value.isascii() or not value.isalpha() or not value.isupper():
            raise ValueError("currency must be an uppercase alphabetic code")
        return value

    @model_validator(mode="after")
    def validate_scope(self) -> OperatorDisclosureRecord:
        if self.scope == ScopeType.PROJECT:
            if self.project_name is None:
                raise ValueError("project scope requires project_name")
            if not self.metric_name_normalized.value.startswith("project_"):
                raise ValueError("project scope requires a project metric")
        else:
            if self.project_name is not None:
                raise ValueError("operator scope forbids project_name")
            if not self.metric_name_normalized.value.startswith("operator_"):
                raise ValueError("operator scope requires an operator metric")
        return self
