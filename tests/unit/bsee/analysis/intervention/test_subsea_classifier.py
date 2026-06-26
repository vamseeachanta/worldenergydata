# ABOUTME: Unit tests for the subsea-vs-dry-tree completion classifier (worldenergydata #584).
# ABOUTME: Pure-function classification + table summary on synthetic frames; real-data run is skip-if-missing.

"""Unit tests for worldenergydata.bsee.analysis.intervention.subsea_classifier."""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.intervention.subsea_classifier import (
    COMPLETION_COL,
    COMPLETION_TYPES,
    SUBSEA,
    SURFACE,
    UNKNOWN,
    build_classification,
    classify_completion,
    classify_tree_height_table,
    cross_validate,
    host_type_context,
    summarize_completions,
)

# The sample CSV is committed in-repo; the registry/structures pickles live on
# the external mount. Resolve both for the skip-if-missing real-data test.
_REPO_ROOT = Path(__file__).resolve().parents[5]
_REAL_CSV = (
    _REPO_ROOT
    / "data"
    / "modules"
    / "bsee"
    / "current"
    / "operations"
    / "ST_BP_and_tree_height.csv"
)
_REAL_REGISTRY = Path(
    "/mnt/ace/worldenergydata/data/modules/bsee/bin/permstruc/mv_subsea_boreholes.bin"
)
_REAL_STRUCTURES = Path(
    "/mnt/ace/worldenergydata/data/modules/bsee/bin/platstruc/mv_platstruc_structures.bin"
)


class TestClassifyCompletion:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (15.0, SUBSEA),
            (22, SUBSEA),
            (0.0, SUBSEA),  # a present (zero) height is still "on record"
            ("17", SUBSEA),
            (None, SURFACE),
            (float("nan"), SURFACE),
            ("", SURFACE),
            ("   ", SURFACE),
            ("not-a-number", UNKNOWN),
            ("12ft", UNKNOWN),
        ],
    )
    def test_cases(self, value, expected):
        assert classify_completion(value) == expected

    def test_returns_only_known_labels(self):
        for v in [10.0, None, "x"]:
            assert classify_completion(v) in COMPLETION_TYPES


class TestClassifyTable:
    def _frame(self):
        return pd.DataFrame(
            {
                "API_WELL_NUMBER": [1, 2, 3, 4, 5],
                "SUBSEA_TREE_HEIGHT_AML": [15.0, None, 22.0, float("nan"), "junk"],
            }
        )

    def test_adds_completion_column(self):
        out = classify_tree_height_table(self._frame())
        assert COMPLETION_COL in out.columns
        assert list(out[COMPLETION_COL]) == [
            SUBSEA,
            SURFACE,
            SUBSEA,
            SURFACE,
            UNKNOWN,
        ]
        # original frame untouched (copy semantics)
        assert COMPLETION_COL not in self._frame().columns

    def test_missing_column_raises(self):
        with pytest.raises(KeyError):
            classify_tree_height_table(pd.DataFrame({"x": [1]}))

    def test_summary_counts_all_keys(self):
        summary = summarize_completions(classify_tree_height_table(self._frame()))
        assert summary[SUBSEA] == 2
        assert summary[SURFACE] == 2
        assert summary[UNKNOWN] == 1
        assert set(summary.keys()) == set(COMPLETION_TYPES)
        assert sum(summary.values()) == 5

    def test_summary_requires_classified_frame(self):
        with pytest.raises(KeyError):
            summarize_completions(pd.DataFrame({"x": [1]}))


class TestCrossValidate:
    def test_population_counts_and_honesty(self):
        classified = classify_tree_height_table(
            pd.DataFrame({"SUBSEA_TREE_HEIGHT_AML": [15.0, None, 22.0]})
        )
        registry = pd.DataFrame({"WELL_NAME": ["006", "P011", "UI005", "A1"]})
        cv = cross_validate(classified, registry)
        assert cv["sample_subsea_wells"] == 2
        assert cv["sample_total_wells"] == 3
        assert cv["registry_subsea_wells"] == 4
        assert cv["row_level_join_possible"] is False
        assert "no shared key" in cv["join_limitation"].lower()


class TestHostContext:
    def test_floating_vs_fixed_split(self):
        structures = pd.DataFrame(
            {"STRUC_TYPE_CODE": ["FIXED", "FIXED", "SPAR", "TLP", "CAIS", "ZZZ"]}
        )
        ctx = host_type_context(structures)
        assert ctx["floating_dry_tree_capable"] == 2  # SPAR + TLP
        assert ctx["fixed_bottom_founded"] == 3  # FIXED, FIXED, CAIS
        assert ctx["other"] == 1  # ZZZ
        assert ctx["by_struc_type_code"]["FIXED"] == 2


@pytest.mark.skipif(
    not _REAL_CSV.exists(),
    reason="BSEE tree-height sample CSV not available",
)
class TestRealData:
    def test_build_classification_sane_structure(self):
        result = build_classification(
            csv_path=_REAL_CSV,
            registry_path=_REAL_REGISTRY if _REAL_REGISTRY.exists() else None,
            structures_path=_REAL_STRUCTURES if _REAL_STRUCTURES.exists() else None,
        )
        summary = result["summary"]
        # counts partition the sample exactly and are non-negative
        assert set(summary.keys()) == set(COMPLETION_TYPES)
        assert all(v >= 0 for v in summary.values())
        assert (
            summary[SUBSEA] + summary[SURFACE] + summary[UNKNOWN]
            == result["sample_total"]
        )
        assert result["sample_total"] > 0
        assert isinstance(result["caveats"], list) and result["caveats"]
