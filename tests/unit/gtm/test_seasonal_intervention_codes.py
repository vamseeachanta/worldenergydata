"""The gtm intervention report's activity legend must match canonical (#1117).

That report is deliberately stdlib-only, so it cannot import the canonical
definitions artifact and mirrors the legend by hand. A hand-copy with nothing
checking it is exactly how the previous version came to publish three separate
falsehoods:

  - "RC": "Recompletion" and "BP": "Bypass" -- neither code exists in
    mv_war_main_prop. The real token is REC. The published legend therefore
    implied zero recompletions while the same artifact reported three REC
    records with no explanation.
  - "PND": "Pending / sidetrack-bypass" -- an invented meaning for a code BSEE
    does not define.
  - REC, CHZ and the blank code carried data but no legend entry.

These tests make the mirror falsifiable. The stdlib constraint stays; what
changes is that drift now fails the build instead of shipping.
"""

import importlib.util
from pathlib import Path

import pytest

yaml = pytest.importorskip("yaml")

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORT = REPO_ROOT / "reports" / "gtm" / "seasonal_intervention_risk_windows.py"
CANONICAL = (
    REPO_ROOT
    / "packages/worldenergydata-bsee/src/worldenergydata/bsee/analysis/data"
    / "war_activity_codes.yml"
)


def _load_report_module():
    spec = importlib.util.spec_from_file_location("gtm_seasonal", REPORT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def report():
    if not REPORT.exists():  # pragma: no cover - guards a moved report
        pytest.skip(f"report not found: {REPORT}")
    return _load_report_module()


@pytest.fixture(scope="module")
def canonical():
    if not CANONICAL.exists():  # pragma: no cover
        pytest.skip(f"canonical artifact not found: {CANONICAL}")
    return yaml.safe_load(CANONICAL.read_text(encoding="utf-8"))


def _rows(canonical):
    return [r for r in canonical["codes"] if r.get("code")]


class TestEveryCodeIsReal:
    def test_no_legend_entry_names_a_code_that_does_not_exist(self, report, canonical):
        # RC and BP were published as meanings for tokens BSEE never emits.
        real = {r["code"] for r in _rows(canonical)}
        invented = set(report.ACTIVITY_MEANING) - real
        assert not invented, f"legend names codes absent from WAR: {sorted(invented)}"

    def test_the_undocumented_list_is_also_real(self, report, canonical):
        real = {r["code"] for r in _rows(canonical)}
        invented = set(report.ACTIVITY_UNDOCUMENTED) - real
        assert not invented, f"undocumented list names absent codes: {sorted(invented)}"


class TestNoUndocumentedCodeIsGlossed:
    def test_a_code_bsee_does_not_define_carries_no_meaning(self, report, canonical):
        # The load-bearing rule: a bare token beats a confident guess.
        unknown = {
            r["code"] for r in _rows(canonical) if r.get("provenance") == "unknown"
        }
        glossed = unknown & set(report.ACTIVITY_MEANING)
        assert not glossed, f"undocumented codes carry a meaning: {sorted(glossed)}"

    def test_pnd_specifically_is_never_glossed(self, report):
        assert "PND" not in report.ACTIVITY_MEANING
        assert "PND" in report.ACTIVITY_UNDOCUMENTED


class TestTheMirrorMatchesCanonical:
    def test_each_meaning_matches_the_canonical_label(self, report, canonical):
        labels = {r["code"]: r.get("label") for r in _rows(canonical)}
        for code, meaning in report.ACTIVITY_MEANING.items():
            assert (
                labels.get(code) == meaning
            ), f"{code}: report says {meaning!r}, canonical says {labels.get(code)!r}"

    def test_every_documented_code_is_covered_by_one_list_or_the_other(
        self, report, canonical
    ):
        real = {r["code"] for r in _rows(canonical)}
        covered = set(report.ACTIVITY_MEANING) | set(report.ACTIVITY_UNDOCUMENTED)
        missing = real - covered
        assert (
            not missing
        ), f"codes with neither a meaning nor an undocumented entry: {sorted(missing)}"


class TestProvenanceIsStated:
    def test_the_payload_says_these_are_borehole_status_wordings(self, report):
        # Without this a reader assumes BSEE defines WELL_ACTIVITY_CD. It does not.
        text = report.ACTIVITY_MEANING_PROVENANCE
        assert "BOREHOLE_STAT_CD" in text
        assert "inference" in text.lower()
