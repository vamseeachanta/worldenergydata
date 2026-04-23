"""
ABOUTME: Tests for the sanction-side linkage primitive (issue #335).
ABOUTME: Verifies derived-only exact (operator, project_name) matching of
ABOUTME: disclosure project rows to existing CostDataPoint sanction records.

The resolver is intentionally scope-agnostic.  Disclosure-side scope gating
(only project-scope rows may be linked, per #334) is expressed here via the
`disclosure_row_is_linkable()` helper and must be called by consumers before
invoking the resolver.  The resolver itself does no fuzzy matching, aliasing,
case-folding, or whitespace trimming.
"""

from __future__ import annotations

import pytest

from worldenergydata.cost.data_collection.calibration_schema import (
    ActivityType,
    Confidence,
    CostDataPoint,
    CostType,
    RigType,
    SubseaType,
    WaterDepthBand,
    WellDepthBand,
)

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


def _make_cost_point(
    *,
    operator: str = "BP",
    project_name: str = "Mad Dog Phase 2",
    region: str = "GOM",
    cost_usd_mm: float = 145.0,
) -> CostDataPoint:
    """Build a minimal valid CostDataPoint for linkage testing.

    Only the identity fields (operator, project_name) vary between most
    tests; other fields are stable defaults matching the public dataset.
    """
    return CostDataPoint(
        project_name=project_name,
        region=region,
        water_depth_m=1310.0,
        water_depth_band=WaterDepthBand.DEEP,
        well_depth_m=7620.0,
        well_depth_band=WellDepthBand.DEEP,
        operator=operator,
        year_sanction=2017,
        rig_type=RigType.SEMI_SUB,
        activity_type=ActivityType.DRILLING,
        hpht=False,
        subsea=SubseaType.SUBSEA,
        cost_usd_mm=cost_usd_mm,
        cost_type=CostType.TOTAL_CAPEX,
        source="Linkage test fixture",
        confidence=Confidence.HIGH,
    )


# ---------------------------------------------------------------------------
# LinkageStatus enum contract
# ---------------------------------------------------------------------------


class TestLinkageStatusEnum:
    """The linkage contract exposes exactly three canonical states."""

    def test_linkage_status_enum_exposes_linked_unlinked_ambiguous(self):
        """LinkageStatus enum contains LINKED, UNLINKED, and AMBIGUOUS members."""
        from worldenergydata.cost.data_collection.linkage import LinkageStatus

        values = {member.value for member in LinkageStatus}
        assert values == {"linked", "unlinked", "ambiguous"}


# ---------------------------------------------------------------------------
# resolve_cost_datapoint_link outcomes
# ---------------------------------------------------------------------------


class TestResolveOutcomes:
    """resolve_cost_datapoint_link returns explicit linked/unlinked/ambiguous."""

    def test_resolve_link_returns_linked_for_exact_single_match(self):
        """A single exact (operator, project_name) hit yields LINKED."""
        from worldenergydata.cost.data_collection.linkage import (
            LinkageStatus,
            resolve_cost_datapoint_link,
        )

        record = _make_cost_point(operator="BP", project_name="Mad Dog Phase 2")
        result = resolve_cost_datapoint_link(
            operator="BP",
            project_name="Mad Dog Phase 2",
            sanctioned_records=[record],
        )

        assert result.status == LinkageStatus.LINKED
        assert result.matched_record is record
        assert result.matched_count == 1
        assert result.candidates == [record]

    def test_resolve_link_returns_unlinked_for_no_exact_match(self):
        """Zero exact hits yields UNLINKED with no matched record."""
        from worldenergydata.cost.data_collection.linkage import (
            LinkageStatus,
            resolve_cost_datapoint_link,
        )

        record = _make_cost_point(operator="BP", project_name="Mad Dog Phase 2")
        result = resolve_cost_datapoint_link(
            operator="Shell",
            project_name="Penguins",
            sanctioned_records=[record],
        )

        assert result.status == LinkageStatus.UNLINKED
        assert result.matched_record is None
        assert result.matched_count == 0
        assert result.candidates == []

    def test_resolve_link_returns_ambiguous_for_multiple_exact_matches(self):
        """Two or more exact hits yields AMBIGUOUS — no silent guessing."""
        from worldenergydata.cost.data_collection.linkage import (
            LinkageStatus,
            resolve_cost_datapoint_link,
        )

        rec_a = _make_cost_point(
            operator="BP", project_name="Mad Dog Phase 2", cost_usd_mm=145.0
        )
        rec_b = _make_cost_point(
            operator="BP", project_name="Mad Dog Phase 2", cost_usd_mm=180.0
        )
        result = resolve_cost_datapoint_link(
            operator="BP",
            project_name="Mad Dog Phase 2",
            sanctioned_records=[rec_a, rec_b],
        )

        assert result.status == LinkageStatus.AMBIGUOUS
        assert result.matched_count == 2

    def test_ambiguous_result_has_no_single_matched_record(self):
        """AMBIGUOUS outcomes must not commit to a single record."""
        from worldenergydata.cost.data_collection.linkage import (
            resolve_cost_datapoint_link,
        )

        rec_a = _make_cost_point(operator="BP", project_name="Mad Dog Phase 2")
        rec_b = _make_cost_point(
            operator="BP", project_name="Mad Dog Phase 2", cost_usd_mm=200.0
        )
        result = resolve_cost_datapoint_link(
            operator="BP",
            project_name="Mad Dog Phase 2",
            sanctioned_records=[rec_a, rec_b],
        )

        assert result.matched_record is None

    def test_ambiguous_result_preserves_full_candidate_set(self):
        """AMBIGUOUS must carry the full candidate list, not just a count."""
        from worldenergydata.cost.data_collection.linkage import (
            resolve_cost_datapoint_link,
        )

        rec_a = _make_cost_point(
            operator="BP", project_name="Mad Dog Phase 2", cost_usd_mm=145.0
        )
        rec_b = _make_cost_point(
            operator="BP", project_name="Mad Dog Phase 2", cost_usd_mm=180.0
        )
        rec_c = _make_cost_point(
            operator="BP", project_name="Mad Dog Phase 2", cost_usd_mm=210.0
        )
        result = resolve_cost_datapoint_link(
            operator="BP",
            project_name="Mad Dog Phase 2",
            sanctioned_records=[rec_a, rec_b, rec_c],
        )

        # CostDataPoint is not hashable (Pydantic v2 requires frozen=True);
        # compare by membership rather than set equality.
        assert len(result.candidates) == 3
        assert rec_a in result.candidates
        assert rec_b in result.candidates
        assert rec_c in result.candidates


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


class TestLinkResultShape:
    """CostDataPointLinkResult carries the debug/consumer payload."""

    def test_link_result_preserves_match_key_and_match_count(self):
        """The result echoes the lookup key and records the match count."""
        from worldenergydata.cost.data_collection.linkage import (
            resolve_cost_datapoint_link,
        )

        record = _make_cost_point(operator="BP", project_name="Mad Dog Phase 2")
        result = resolve_cost_datapoint_link(
            operator="BP",
            project_name="Mad Dog Phase 2",
            sanctioned_records=[record],
        )

        assert result.match_key_operator == "BP"
        assert result.match_key_project_name == "Mad Dog Phase 2"
        assert result.matched_count == 1


# ---------------------------------------------------------------------------
# Dependency injection semantics
# ---------------------------------------------------------------------------


class TestRecordInjection:
    """sanctioned_records argument distinguishes None (default) from [] (empty)."""

    def test_helper_uses_load_public_dataset_by_default(self):
        """sanctioned_records=None triggers load_public_dataset() fallback."""
        from worldenergydata.cost.data_collection.linkage import (
            resolve_cost_datapoint_link,
        )
        from worldenergydata.cost.data_collection.public_dataset import (
            load_public_dataset,
        )

        # Pick any stable record from the real public dataset as a lookup key.
        real = load_public_dataset()[0]
        result = resolve_cost_datapoint_link(
            operator=real.operator,
            project_name=real.project_name,
        )
        # We only assert the resolver actually consulted the default loader;
        # it must produce at least one candidate for a real dataset key.
        assert result.matched_count >= 1

    def test_helper_respects_injected_empty_record_list(self):
        """sanctioned_records=[] must NOT fall back to load_public_dataset()."""
        from worldenergydata.cost.data_collection.linkage import (
            LinkageStatus,
            resolve_cost_datapoint_link,
        )

        result = resolve_cost_datapoint_link(
            operator="BP",
            project_name="Mad Dog Phase 2",
            sanctioned_records=[],
        )

        assert result.status == LinkageStatus.UNLINKED
        assert result.matched_count == 0

    def test_helper_accepts_injected_records_for_testing(self):
        """Injected lists override the default loader for deterministic tests."""
        from worldenergydata.cost.data_collection.linkage import (
            LinkageStatus,
            resolve_cost_datapoint_link,
        )

        injected = [
            _make_cost_point(operator="Fictional Co", project_name="Nowhere Field"),
        ]
        result = resolve_cost_datapoint_link(
            operator="Fictional Co",
            project_name="Nowhere Field",
            sanctioned_records=injected,
        )

        assert result.status == LinkageStatus.LINKED
        assert result.matched_record is injected[0]


# ---------------------------------------------------------------------------
# No hidden normalization
# ---------------------------------------------------------------------------


class TestExactnessIsStrict:
    """No trimming, case-folding, or alias handling is permitted."""

    @pytest.mark.parametrize(
        "operator,project_name",
        [
            ("bp", "Mad Dog Phase 2"),            # lowercased operator
            ("BP", "mad dog phase 2"),            # lowercased project
            ("  BP  ", "Mad Dog Phase 2"),        # padded operator
            ("BP", "Mad Dog Phase 2 "),           # trailing space on project
            ("BP", "Mad-Dog Phase 2"),            # punctuation variant
        ],
    )
    def test_negative_exactness_case_changes_stay_unlinked(
        self, operator, project_name
    ):
        """Any case/whitespace/punctuation variant yields UNLINKED."""
        from worldenergydata.cost.data_collection.linkage import (
            LinkageStatus,
            resolve_cost_datapoint_link,
        )

        record = _make_cost_point(operator="BP", project_name="Mad Dog Phase 2")
        result = resolve_cost_datapoint_link(
            operator=operator,
            project_name=project_name,
            sanctioned_records=[record],
        )

        assert result.status == LinkageStatus.UNLINKED


# ---------------------------------------------------------------------------
# Operator-scope invariant (parent #334 invariant, enforced by caller gate)
# ---------------------------------------------------------------------------


class TestOperatorScopeNonLinkability:
    """Operator-scope disclosure rows are never linkable; gate lives here."""

    def test_operator_scope_rows_are_never_linkable(self):
        """`disclosure_row_is_linkable('operator')` is False; project is True."""
        from worldenergydata.cost.data_collection.linkage import (
            disclosure_row_is_linkable,
        )

        assert disclosure_row_is_linkable("project") is True
        assert disclosure_row_is_linkable("operator") is False

    def test_operator_scope_bypass_attempt_does_not_link(self):
        """Correct consumer flow filters operator rows out before the resolver.

        The resolver itself has no scope knowledge; the contract is that
        consumers call disclosure_row_is_linkable() first.  If a consumer
        respects the gate, no operator-scope row can reach the resolver,
        regardless of whether the operator name happens to match a sanction
        record.
        """
        from worldenergydata.cost.data_collection.linkage import (
            disclosure_row_is_linkable,
            resolve_cost_datapoint_link,
        )

        # An operator-scope row only has operator, no project_name.
        disclosure_scope = "operator"
        disclosure_operator = "BP"
        # Sanction record exists with the same operator — the bypass risk.
        sanction_record = _make_cost_point(
            operator="BP", project_name="Mad Dog Phase 2"
        )

        # Correct consumer gate: never invoke resolver for operator rows.
        if disclosure_row_is_linkable(disclosure_scope):
            pytest.fail(
                "operator-scope row must be rejected before the resolver is called"
            )

        # Even if a consumer bypassed the gate and routed the operator name
        # to the resolver with an empty/missing project_name, the result must
        # not be LINKED, because the resolver demands an exact project match.
        from worldenergydata.cost.data_collection.linkage import LinkageStatus

        bypass_result = resolve_cost_datapoint_link(
            operator=disclosure_operator,
            project_name="",
            sanctioned_records=[sanction_record],
        )
        assert bypass_result.status != LinkageStatus.LINKED


# ---------------------------------------------------------------------------
# Invalid/empty inputs
# ---------------------------------------------------------------------------


class TestInvalidInputs:
    """None or empty operator/project_name fail safely as UNLINKED."""

    @pytest.mark.parametrize(
        "operator,project_name",
        [
            (None, "Mad Dog Phase 2"),
            ("BP", None),
            ("", "Mad Dog Phase 2"),
            ("BP", ""),
            (None, None),
        ],
    )
    def test_none_or_empty_operator_or_project_returns_unlinked(
        self, operator, project_name
    ):
        """Missing key components yield UNLINKED, never an exception."""
        from worldenergydata.cost.data_collection.linkage import (
            LinkageStatus,
            resolve_cost_datapoint_link,
        )

        record = _make_cost_point(operator="BP", project_name="Mad Dog Phase 2")
        result = resolve_cost_datapoint_link(
            operator=operator,
            project_name=project_name,
            sanctioned_records=[record],
        )

        assert result.status == LinkageStatus.UNLINKED
        assert result.matched_count == 0


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------


class TestDataCollectionExports:
    """worldenergydata.cost.data_collection re-exports the linkage contract."""

    def test_data_collection_exports_linkage_contract(self):
        """Linkage primitives are reachable from the top-level package module."""
        import worldenergydata.cost.data_collection as data_collection

        assert hasattr(data_collection, "LinkageStatus")
        assert hasattr(data_collection, "CostDataPointLinkResult")
        assert hasattr(data_collection, "resolve_cost_datapoint_link")
        assert hasattr(data_collection, "disclosure_row_is_linkable")


# ---------------------------------------------------------------------------
# Regression boundary — sanction dataset loader is unchanged
# ---------------------------------------------------------------------------


class TestLoadPublicDatasetUnchanged:
    """load_public_dataset() still returns its original shape/type."""

    def test_load_public_dataset_shape_is_unchanged(self):
        """Loader still returns list[CostDataPoint] with >=20 records."""
        from worldenergydata.cost.data_collection.public_dataset import (
            load_public_dataset,
        )

        records = load_public_dataset()
        assert isinstance(records, list)
        assert len(records) >= 20
        for rec in records:
            assert isinstance(rec, CostDataPoint)
