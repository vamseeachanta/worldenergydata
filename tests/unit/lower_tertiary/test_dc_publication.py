"""Publication requires recorded provenance; historical inspection stays available.

Contract source: issue #1076, Acceptance (2026): no published day count
without a basis. Fixtures use synthetic labels and no physical coefficients.
"""

import sys
from types import SimpleNamespace

import pandas as pd
import pytest

from tests.unit.lower_tertiary.test_dc_provenance import REPO, load_script


@pytest.mark.parametrize("missing", ["basis", "pnd_days", "days_status"])
@pytest.mark.parametrize("surface", ["listing", "drilldown", "vintage", "dataset"])
def test_publication_refuses_missing_provenance_before_writing(
    monkeypatch, tmp_path, surface, missing
):
    """Removing any required label must leave existing output bytes intact."""
    row = {"basis": "synthetic rule", "pnd_days": None, "days_status": "war_covered"}
    row.pop(missing)
    target = tmp_path / "retained-output"
    original = b"previous publication\n"
    target.write_bytes(original)
    if surface == "listing":
        mod = load_script(REPO / "scripts/lower_tertiary/build_wo_per_well_dc.py")
        monkeypatch.setattr(mod, "load_bores", lambda: {"synthetic": [row]})
        monkeypatch.setattr(mod, "load_vintage_diff", dict)
        monkeypatch.setattr(mod, "OUT_MD", target)
    elif surface == "drilldown":
        mod = load_script(REPO / "scripts/lower_tertiary/build_dc_drilldown.py")
        monkeypatch.setattr(
            mod,
            "load_payload",
            lambda: {key: [row] for key in ("bores", "fields", "blocks")},
        )
        monkeypatch.setattr(mod, "OUT_HTML", target)
    elif surface == "vintage":
        mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
        monkeypatch.setattr(
            mod.pd,
            "ExcelFile",
            lambda _: SimpleNamespace(parse=lambda _: pd.DataFrame()),
        )
        monkeypatch.setattr(mod.pd, "read_csv", lambda *_, **__: pd.DataFrame())
        monkeypatch.setattr(mod, "build_diff", lambda *_: pd.DataFrame([row]))
        monkeypatch.setattr(mod, "OUT_CSV", target)
    else:
        mod = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
        monkeypatch.setattr(sys, "argv", ["publish_dc_days_to_hf.py", "--dry-run"])
        monkeypatch.setattr(
            mod, "build_tables", lambda: {"synthetic": pd.DataFrame([row])}
        )

    with pytest.raises(ValueError, match="provenance"):
        mod.main()
    assert target.read_bytes() == original


@pytest.mark.parametrize("invalid", [None, "", " ", "unavailable", "nan"])
def test_publication_refuses_unrecorded_basis(invalid):
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    row = {"basis": invalid, "pnd_days": None, "days_status": "no_war_activity"}
    with pytest.raises(ValueError, match="provenance"):
        mod.require_publication_provenance([row])


@pytest.mark.parametrize("basis", ["synthetic rule", "mixed"])
def test_publication_accepts_recorded_or_explicitly_mixed_basis(basis):
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    mod.require_publication_provenance(
        [{"basis": basis, "pnd_days": None, "days_status": "war_covered"}]
    )


def test_publication_checks_every_row():
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    good = {"basis": "synthetic rule", "pnd_days": None, "days_status": "war_covered"}
    with pytest.raises(ValueError, match="provenance"):
        mod.require_publication_provenance([good, dict(good, days_status=" ")])


@pytest.mark.parametrize("side", ["v30", "wed"])
def test_publication_requires_each_present_vintage_basis(side):
    """One synthetic day on each side needs both rules, even if delta is zero."""
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    row = {
        "basis": "synthetic rule",
        "basis_v30": "synthetic rule",
        "basis_wed": "synthetic rule",
        "pnd_days": None,
        "days_status": "war_covered",
        "drill_v30": 1,
        "drill_wed": 1,
        "category": "unchanged",
    }
    row[f"basis_{side}"] = None
    with pytest.raises(ValueError, match="provenance"):
        mod.require_publication_provenance([row])


@pytest.mark.parametrize("present,absent", [("v30", "wed"), ("wed", "v30")])
def test_publication_allows_absent_vintage_side(present, absent):
    """An outer-join-only bore has no source row on its absent side."""
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    mod.require_publication_provenance(
        [
            dict(
                basis="synthetic rule",
                pnd_days=None,
                days_status="war_covered",
                drill_v30=0,
                drill_wed=0,
                category=f"{present}_only",
                **{f"basis_{present}": "synthetic rule", f"basis_{absent}": None},
            )
        ]
    )


@pytest.mark.parametrize("uniform", [True, False])
def test_field_and_block_totals_record_one_basis_or_mixed(
    monkeypatch, tmp_path, uniform
):
    """Hand calculation for the existing synthetic fixture: drill = 0 + 3,
    completion = 0 + 2. Equal rules give that rule; distinct rules give mixed.
    The fixture's unknown PND contributor makes the PND total unknown.
    """
    from tests.unit.lower_tertiary.test_dc_provenance import (
        patch_inputs,
        synthetic_inputs,
        write_rows,
    )

    inputs = synthetic_inputs.__wrapped__(tmp_path)
    rows = pd.read_csv(inputs[0], dtype=str).fillna("").to_dict("records")
    if uniform:
        for row in rows:
            row["BASIS"] = "synthetic rule"
        write_rows(inputs[0], rows)
    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_drilldown.py")
    patch_inputs(monkeypatch, mod, inputs)
    payload = mod.load_payload()
    for surface in ("fields", "blocks"):
        for total in payload[surface]:
            assert total["basis"] == ("synthetic rule" if uniform else "mixed")
            assert (total["drill"], total["compl"]) == (3, 2)
            assert total["pnd_days"] is None


@pytest.mark.parametrize("surface", ["listing", "drilldown", "vintage"])
def test_labelled_report_command_writes_output(monkeypatch, tmp_path, surface):
    """Recorded synthetic labels must survive real file loading and writing."""
    from tests.unit.lower_tertiary.test_dc_provenance import (
        add_source_labels,
        patch_inputs,
        synthetic_inputs,
        synthetic_vintages,
    )

    inputs = synthetic_inputs.__wrapped__(tmp_path)
    vintage = pd.read_csv(inputs[2]).assign(
        basis="synthetic rule",
        basis_v30="synthetic rule",
        basis_wed="synthetic rule",
        pnd_days=None,
        days_status="war_covered",
    )
    vintage.to_csv(inputs[2], index=False)
    target = tmp_path / "published-output"
    if surface == "vintage":
        mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
        old, new = synthetic_vintages()
        old_path, new_path = tmp_path / "frozen.xlsx", tmp_path / "candidate.csv"
        add_source_labels(old, "synthetic rule").to_excel(old_path, index=False)
        add_source_labels(new, "synthetic rule").to_csv(new_path, index=False)
        monkeypatch.setattr(mod, "FROZEN_XLSX", old_path)
        monkeypatch.setattr(mod, "CANDIDATE_CSV", new_path)
        monkeypatch.setattr(mod, "OUT_CSV", target)
    else:
        name, output = (
            ("build_wo_per_well_dc.py", "OUT_MD")
            if surface == "listing"
            else ("build_dc_drilldown.py", "OUT_HTML")
        )
        mod = load_script(REPO / "scripts/lower_tertiary" / name)
        patch_inputs(monkeypatch, mod, inputs)
        monkeypatch.setattr(mod, output, target)
    mod.main()
    text = target.read_text(encoding="utf-8")
    assert "synthetic rule" in text
    assert "war_covered" in text
