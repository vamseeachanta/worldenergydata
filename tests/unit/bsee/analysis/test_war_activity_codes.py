"""Tests for the canonical WAR ``WELL_ACTIVITY_CD`` definition source (#1065).

The vocabulary used to exist in four disconnected copies, and the uncertainty
flag on ``PND`` was lost in the copying. These tests pin the three properties
that stop that happening again:

1.  The YAML parses and covers exactly the codes that occur in the data.
2.  Every ``unknown`` row has a ``null`` label -- this is the guard that stops a
    meaning being attached to an undocumented code later.
3.  ``WAR_ACTIVITY_LABELS`` still resolves, unchanged, for its existing
    consumers, so no published number moves.
"""

from pathlib import Path

import pandas as pd
import pytest

from worldenergydata.bsee.analysis.war_activity_codes import (
    PROVENANCE_PUBLISHED_OTHER_DOMAIN,
    PROVENANCE_UNKNOWN,
    activity_codes,
    activity_labels,
    codes_yaml_path,
    load_activity_codes,
    undocumented_codes,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
WAR_FIXTURES = (
    REPO_ROOT / "docs/modules/bsee/analysis/rig_days/war_data_608124009500.csv",
    REPO_ROOT / "docs/modules/bsee/analysis/rig_days/war_data_608124003301.csv",
)

# Observed in mv_war_main_prop (2026-02-19 vintage, 361,756 rows). The null code
# (882 rows, WAR weeks 1997-2002) is carried in the YAML as a `code: null`
# row but is a missing value rather than a token, so it is not in this set.
CORPUS_CODES = {
    "DRL",
    "COM",
    "TA",
    "PA",
    "ST",
    "DSI",
    "WO",
    "CHZ",
    "PND",
    "MPF",
    "REC",
    "TBK",
}

#: BSEE has published no meaning for these in any domain.
EXPECTED_UNDOCUMENTED = {"WO", "PND", "CHZ", "MPF", "REC", "TBK"}


class TestYamlIsWellFormed:
    def test_canonical_yaml_ships_with_the_package(self):
        # It must sit inside the installed package, not in docs/, or it cannot
        # be imported by the code that depends on it.
        assert codes_yaml_path().exists(), codes_yaml_path()
        assert codes_yaml_path().name == "war_activity_codes.yml"

    def test_yaml_parses(self):
        doc = load_activity_codes()
        assert doc["meta"]["field"] == "WELL_ACTIVITY_CD"
        assert doc["meta"]["source_table"] == "mv_war_main_prop"
        assert isinstance(doc["codes"], list) and doc["codes"]

    def test_records_that_bsee_publishes_no_domain_for_this_field(self):
        # The headline finding. If this ever flips to True, every `unknown`
        # row below is up for revision -- and only then.
        meta = load_activity_codes()["meta"]
        assert meta["published_domain_found"] is False
        # ...with the surfaces that were checked, so the claim is auditable.
        assert len(meta["searched"]) >= 5

    def test_every_row_declares_a_provenance(self):
        for row in load_activity_codes()["codes"]:
            assert row.get("provenance") in {
                PROVENANCE_UNKNOWN,
                PROVENANCE_PUBLISHED_OTHER_DOMAIN,
            }, row


class TestNoMeaningIsAttachedToUnknownCodes:
    """The guard this whole file exists for."""

    def test_every_unknown_row_has_a_null_label(self):
        offenders = [
            row["code"]
            for row in load_activity_codes()["codes"]
            if row.get("provenance") == PROVENANCE_UNKNOWN
            and row.get("label") is not None
        ]
        assert not offenders, (
            f"A meaning was attached to undocumented code(s) {offenders}. "
            "BSEE publishes no definition for these; `label` must stay null "
            "until they answer (#1065)."
        )

    def test_activity_labels_omits_undocumented_codes(self):
        labelled = set(activity_labels())
        assert not (labelled & EXPECTED_UNDOCUMENTED), (
            "activity_labels() must not offer a label for a code BSEE has "
            "never defined; render the bare code instead."
        )

    def test_undocumented_set_is_the_expected_six(self):
        assert undocumented_codes() == EXPECTED_UNDOCUMENTED

    def test_labelled_codes_are_flagged_as_borrowed_from_another_domain(self):
        # Their labels are real BSEE text, but from BOREHOLE_STAT_CD; the reuse
        # as an activity code is our inference and must stay marked as such.
        for row in load_activity_codes()["codes"]:
            if row.get("provenance") == PROVENANCE_PUBLISHED_OTHER_DOMAIN:
                assert row["published_in"] == "BOREHOLE_STAT_CD", row
                assert row["reuse_inferred"] is True, row
                assert row["label"], row

    def test_pnd_carries_no_label_and_names_its_blocking_issue(self):
        pnd = next(r for r in load_activity_codes()["codes"] if r.get("code") == "PND")
        assert pnd["label"] is None
        assert pnd["provenance"] == PROVENANCE_UNKNOWN
        assert pnd["blocks_issue"] == 1065


class TestCodeSetMatchesTheData:
    def test_code_set_matches_the_corpus_inventory(self):
        assert activity_codes() == CORPUS_CODES

    def test_a_null_code_row_is_carried_for_the_pre_ewell_rows(self):
        # 882 rows carry no code at all. Recorded, but not a token.
        nulls = [r for r in load_activity_codes()["codes"] if r.get("code") is None]
        assert len(nulls) == 1
        assert nulls[0]["label"] is None
        assert None not in activity_codes()

    @pytest.mark.parametrize("fixture", WAR_FIXTURES, ids=lambda p: p.stem)
    def test_every_code_in_the_committed_war_fixtures_is_defined(self, fixture):
        if not fixture.exists():  # pragma: no cover - guards a moved fixture
            pytest.skip(f"WAR fixture not found: {fixture}")
        observed = set(pd.read_csv(fixture)["WELL_ACTIVITY_CD"].dropna().astype(str))
        assert observed, f"fixture has no activity codes: {fixture}"
        assert observed <= activity_codes(), observed - activity_codes()

    def test_the_outstanding_ask_covers_every_undocumented_code(self):
        # Not PND alone -- the whole domain. Under-asking is how this recurs.
        ask = set(load_activity_codes()["outstanding_query"]["codes"])
        assert ask == EXPECTED_UNDOCUMENTED


class TestBackwardsCompatibility:
    """``WAR_ACTIVITY_LABELS`` must resolve, unchanged, for its consumers."""

    #: Verbatim, the dict that ops_timeline hand-maintained before #1065. These
    #: are DISPLAY strings, not definitions; lower_tertiary.well_benchmark
    #: selects interventions by matching them exactly, so drift here silently
    #: moves published intervention counts.
    FROZEN = {
        "DRL": "Drilling",
        "COM": "Completion",
        "WO": "Workover",
        "REC": "Recompletion",
        "ST": "Sidetrack",
        "CHZ": "Casing/Hole repair",
        "TA": "Temporary abandonment",
        "PA": "Plug & abandon",
        "PND": "Pending / suspended",
        "DSI": "Drilling suspended",
        "MPF": "Multi-phase / facility work",
        "TBK": "Test / tubing work",
    }

    def test_ops_timeline_export_is_byte_identical_to_the_old_dict(self):
        from worldenergydata.lower_tertiary.ops_timeline import (
            WAR_ACTIVITY_LABELS,
        )

        assert WAR_ACTIVITY_LABELS == self.FROZEN

    def test_war_rig_days_reexport_still_resolves(self):
        from worldenergydata.bsee.analysis.war_rig_days import (
            WAR_ACTIVITY_LABELS,
        )

        assert WAR_ACTIVITY_LABELS == self.FROZEN

    def test_well_benchmark_intervention_strings_still_match(self):
        # The concrete coupling: these exact strings drive an .isin() filter.
        from worldenergydata.lower_tertiary.ops_timeline import (
            INTERVENTION_CODES,
            WAR_ACTIVITY_LABELS,
        )
        from worldenergydata.lower_tertiary.well_benchmark import (
            _INTERVENTION_OPS,
        )

        rendered = {WAR_ACTIVITY_LABELS[c] for c in INTERVENTION_CODES}
        assert rendered & _INTERVENTION_OPS == {
            "Workover",
            "Recompletion",
            "Sidetrack",
        }

    def test_labels_are_derived_from_the_yaml_not_hand_maintained(self):
        # Every display string must be traceable to a row in the canonical
        # file, so a code cannot be added in one place and missed in another.
        from worldenergydata.lower_tertiary.ops_timeline import (
            WAR_ACTIVITY_LABELS,
        )

        by_code = {
            r["code"]: r
            for r in load_activity_codes()["codes"]
            if r.get("code") is not None
        }
        assert set(WAR_ACTIVITY_LABELS) == set(by_code)
        for code, shown in WAR_ACTIVITY_LABELS.items():
            assert by_code[code]["legacy_display_label"] == shown


class TestTheInvariantIsEnforcedNotJustDocumented:
    """Adversarial-review regressions: the loader must refuse, not trust.

    The generator already refuses to render a meaning for an undocumented code.
    These pin the same rule one layer down, because a rule enforced in only one
    place is a rule that erodes the first time someone edits the other place.
    """

    def test_a_label_on_an_unknown_row_raises_rather_than_publishing(self, tmp_path):
        # The failure this prevents: an editor adds `label: Pending` to PND but
        # leaves `provenance: unknown`, and the guess ships as a definition.
        import yaml

        from worldenergydata.bsee.analysis import war_activity_codes as mod

        doc = yaml.safe_load(mod.codes_yaml_path().read_text(encoding="utf-8"))
        for row in doc["codes"]:
            if row.get("provenance") == mod.PROVENANCE_UNKNOWN and row.get("code"):
                row["label"] = "Pending"
                break

        poisoned = tmp_path / "poisoned.yml"
        poisoned.write_text(yaml.safe_dump(doc), encoding="utf-8")

        # Point the module's default path at the poisoned file. Calling
        # load_activity_codes(poisoned) would NOT work: the loader is cached
        # per-argument, so the no-arg call inside activity_labels() would miss
        # that cache entry and read the real artifact instead.
        original = mod._CODES_YML
        mod._CODES_YML = poisoned
        mod.load_activity_codes.cache_clear()
        mod.activity_labels.cache_clear()
        try:
            with pytest.raises(ValueError, match="provenance 'unknown'"):
                mod.activity_labels()
        finally:
            mod._CODES_YML = original
            mod.load_activity_codes.cache_clear()
            mod.activity_labels.cache_clear()

    def test_a_truncated_artifact_raises_rather_than_returning_a_partial_map(
        self, tmp_path
    ):
        # A syntactically valid file carrying only `meta` previously yielded an
        # empty mapping, which would publish a complete-looking page with codes
        # silently missing.
        from worldenergydata.bsee.analysis import war_activity_codes as mod

        truncated = tmp_path / "truncated.yml"
        truncated.write_text("meta:\n  field: WELL_ACTIVITY_CD\n", encoding="utf-8")

        mod.load_activity_codes.cache_clear()
        try:
            with pytest.raises(ValueError, match="no 'codes' section"):
                mod.load_activity_codes(truncated)
        finally:
            mod.load_activity_codes.cache_clear()

    def test_the_label_mapping_cannot_be_mutated_by_a_caller(self):
        # It is cached, so an in-place edit would poison every later reader.
        from worldenergydata.bsee.analysis import war_activity_codes as mod

        labels = mod.activity_labels()
        with pytest.raises(TypeError):
            labels["PND"] = "Pending"
