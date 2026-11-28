"""Collect the published r15 comparison checks in the PR reporting shard."""

from examples.bsee.issue2_public_data_r15.tests.test_comparison import (
    test_committed_comparison_recomputes_from_both_revisions,
    test_only_seven_input_and_exclusion_counts_changed,
    test_published_headlines_are_unchanged,
)

__all__ = [
    "test_committed_comparison_recomputes_from_both_revisions",
    "test_only_seven_input_and_exclusion_counts_changed",
    "test_published_headlines_are_unchanged",
]
