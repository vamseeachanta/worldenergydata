"""Shared polite fetch infrastructure for public state-regulator sources."""

from .client import Fetcher
from .policy import (
    BudgetExceeded,
    FetchConfig,
    TermsCheck,
    TermsDenied,
    UnreachableTarget,
    choose_route,
    header_delay,
)
from .storage import FetchResult

__all__ = [
    "BudgetExceeded",
    "FetchConfig",
    "Fetcher",
    "FetchResult",
    "TermsCheck",
    "TermsDenied",
    "UnreachableTarget",
    "choose_route",
    "header_delay",
]
