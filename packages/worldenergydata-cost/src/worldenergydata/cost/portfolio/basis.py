"""Fail-closed cost bases and counting evidence.

Source: repository cost synthesis plan (2026), eligibility and ledger rules.
No FX, ownership gross-up, phase conversion or scope allocation is inferred.
"""

from __future__ import annotations

from dataclasses import dataclass, fields

from .intervals import Interval


def known(value: str) -> bool:
    return (
        isinstance(value, str)
        and bool(value.strip())
        and value.strip().lower()
        not in {
            "unknown",
            "none",
            "n/a",
            "todo",
            "not_public",
            "tbd",
            "-",
            "na",
            "null",
            "nan",
            "not applicable",
            "not available",
        }
    )


@dataclass(frozen=True)
class Basis:
    currency: str
    price_basis: str
    ownership: str
    scope: str
    capex: str
    phase: str
    basis_year: int | None = None

    def __post_init__(self) -> None:
        if any(
            not known(getattr(self, f.name))
            for f in fields(self)
            if f.name != "basis_year"
        ):
            raise ValueError("all basis dimensions must be known")
        if self.basis_year is not None and (
            type(self.basis_year) is not int or not 1 <= self.basis_year <= 9999
        ):
            raise ValueError("basis year must be an integer calendar year")
        if self.price_basis.strip().lower() != "nominal" and self.basis_year is None:
            raise ValueError("non-nominal money requires an explicit basis year")


@dataclass(frozen=True)
class Project:
    project_id: str
    architecture: str
    total: Interval
    basis: Basis
    requirement_ids: tuple[str, ...]
    source: str

    def __post_init__(self) -> None:
        if not all(known(v) for v in (self.project_id, self.architecture, self.source)):
            raise ValueError("project identity, architecture and source must be known")
        if self.total.low < 0:
            raise ValueError("negative project total")
        if not self.requirement_ids or len(set(self.requirement_ids)) != len(
            self.requirement_ids
        ):
            raise ValueError("unique requirement identities required")
        if any(not known(v) for v in self.requirement_ids):
            raise ValueError("known requirements required")


@dataclass(frozen=True)
class Contribution:
    award_id: str
    requirement_ids: tuple[str, ...]
    amount: Interval | None
    basis: Basis
    disposition: str
    value_basis: str
    source: str
    reason: str = ""
    overlap_group: str | None = None

    def __post_init__(self) -> None:
        if not known(self.award_id) or not known(self.source):
            raise ValueError("award identity and source required")
        if self.disposition not in {"included", "excluded", "overlap"}:
            raise ValueError("invalid counting disposition")
        if self.disposition != "included" and not known(self.reason):
            raise ValueError("excluded and overlap rows require a reason")
        if self.disposition == "included" and self.reason:
            raise ValueError("included rows cannot carry an exclusion reason")
        if self.disposition == "overlap" and not known(self.overlap_group):
            raise ValueError("overlap disposition requires an overlap group")
        if self.amount is not None and self.amount.low < 0:
            raise ValueError("negative award cost")
        if self.value_basis not in {
            "point",
            "range",
            "band",
            "not_public",
            "combined",
            "lease_contract",
            "midstream",
            "backlog",
        }:
            raise ValueError("unrecognized value basis")
        if (self.amount is None) != (self.value_basis == "not_public"):
            raise ValueError("only not_public has no amount")
        if self.value_basis == "point" and self.amount.low != self.amount.high:
            raise ValueError("point value requires equal endpoints")

    def validate_for(self, project: Project) -> None:
        if self.disposition != "included":
            return
        if not self.requirement_ids or not set(self.requirement_ids) <= set(
            project.requirement_ids
        ):
            raise ValueError("included award references unknown requirement")
        if self.amount is None:
            return  # An undisclosed award is visible but contributes no money.
        if self.value_basis not in {"point", "range", "band"}:
            raise ValueError(
                "unsafe value basis requires exclusion or a separate sourced split"
            )
        if self.basis != project.basis:
            raise ValueError("incompatible comparison basis")
