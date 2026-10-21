"""Publication requires recorded provenance; historical inspection stays available.

Contract source: issue #1076, Acceptance (2026): no published day count
without a basis. Fixtures use synthetic labels and no physical coefficients.
"""

import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
import pytest

from tests.unit.lower_tertiary.test_dc_provenance import REPO, load_script


@pytest.mark.parametrize("missing", ["basis", "pnd_days", "days_status"])
@pytest.mark.parametrize("surface", ["listing", "drilldown", "vintage"])
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

    with pytest.raises(ValueError, match="provenance"):
        mod.main()
    assert target.read_bytes() == original


@pytest.mark.parametrize("missing", ["basis", "pnd_days", "days_status"])
def test_dataset_refuses_missing_provenance_before_staging_or_upload(
    monkeypatch, missing
):
    mod = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
    tables = labelled_dataset_tables()
    tables["dc_bores"] = tables["dc_bores"].drop(columns=missing)
    monkeypatch.setattr(sys, "argv", ["publish_dc_days_to_hf.py"])
    monkeypatch.setattr(mod, "build_tables", lambda: tables)
    staging, api = Mock(), Mock()
    monkeypatch.setattr(mod.tempfile, "mkdtemp", staging)
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(HfApi=api, hf_hub_download=Mock()),
    )

    with pytest.raises(ValueError, match="provenance"):
        mod.main()
    staging.assert_not_called()
    api.assert_not_called()


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


@pytest.mark.parametrize(
    "status",
    ["war_covered", "no_war_activity", "war_covered_no_activity_code", "mixed"],
)
def test_publication_accepts_source_coverage_vocabulary(status):
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    mod.require_publication_provenance(
        [{"basis": "synthetic rule", "pnd_days": None, "days_status": status}]
    )


@pytest.mark.parametrize(
    "status",
    ["unknown", "measured", "war_coverd", "MIXED", " war_covered ", None, 0, pd.NA],
)
def test_publication_refuses_unsupported_coverage_status(status):
    mod = load_script(REPO / "scripts/lower_tertiary/dc_provenance.py")
    with pytest.raises(ValueError, match="provenance status"):
        mod.require_publication_provenance(
            [{"basis": "synthetic rule", "pnd_days": None, "days_status": status}]
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
    """Equal rules give that rule; distinct rules give mixed.
    The fixture's unknown PND contributor makes the PND total unknown.
    """
    from tests.unit.lower_tertiary.test_dc_provenance import (
        make_synthetic_inputs,
        patch_inputs,
        write_rows,
    )

    inputs = make_synthetic_inputs(tmp_path)
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
            assert total["pnd_days"] is None


@pytest.mark.parametrize("surface", ["listing", "drilldown", "vintage"])
def test_labelled_report_command_writes_output(monkeypatch, tmp_path, surface):
    """Recorded synthetic labels must survive real file loading and writing."""
    from tests.unit.lower_tertiary.test_dc_provenance import (
        add_source_labels,
        make_synthetic_inputs,
        patch_inputs,
        synthetic_vintages,
    )

    inputs = make_synthetic_inputs(tmp_path)
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


def test_unlabelled_frozen_workbook_blocks_publication_without_modification(
    monkeypatch, tmp_path
):
    """Candidate provenance cannot establish a rule for the frozen side."""
    from tests.unit.lower_tertiary.test_dc_provenance import (
        add_source_labels,
        synthetic_vintages,
    )

    mod = load_script(REPO / "scripts/lower_tertiary/build_dc_vintage_diff.py")
    old, new = synthetic_vintages()
    old_path, new_path = tmp_path / "frozen.xlsx", tmp_path / "candidate.csv"
    old.to_excel(old_path, index=False)
    original = old_path.read_bytes()
    add_source_labels(new, "synthetic rule").to_csv(new_path, index=False)
    target = tmp_path / "retained-output.csv"
    target.write_bytes(b"previous publication\n")
    monkeypatch.setattr(mod, "FROZEN_XLSX", old_path)
    monkeypatch.setattr(mod, "CANDIDATE_CSV", new_path)
    monkeypatch.setattr(mod, "OUT_CSV", target)

    with pytest.raises(ValueError, match="provenance for vintage side"):
        mod.main()
    assert old_path.read_bytes() == original
    assert target.read_bytes() == b"previous publication\n"


def labelled_dataset_tables():
    """Synthetic snapshot pins satisfy the unchanged command assertions."""
    labels = {"basis": "synthetic rule", "pnd_days": None, "days_status": "war_covered"}
    tables = {
        "dc_development_summary": pd.DataFrame(
            [dict(labels, dc_days_wed=25404, delta_days=195)]
        ),
        "dc_bores": pd.DataFrame([dict(labels, drilling_days=1)] * 253),
        "dc_vintage_diff": pd.DataFrame(
            [
                dict(
                    labels,
                    basis_v30="synthetic rule",
                    basis_wed="synthetic rule",
                    drill_v30=1,
                    drill_wed=1,
                    category="unchanged",
                )
            ]
            * 253
        ),
    }
    for table in tables.values():
        table["pnd_days"] = table["pnd_days"].astype("Int64")
    return tables


def test_labelled_dataset_dry_run_writes_without_upload(monkeypatch, tmp_path, capsys):
    """All three labelled tables round-trip without an upload or card download."""
    mod = load_script(REPO / "scripts/hf_export/publish_dc_days_to_hf.py")
    tables = labelled_dataset_tables()
    staging = tmp_path / "dataset"
    staging.mkdir()
    make_staging, api, download = Mock(return_value=str(staging)), Mock(), Mock()
    monkeypatch.setattr(sys, "argv", ["publish_dc_days_to_hf.py", "--dry-run"])
    monkeypatch.setattr(mod, "build_tables", lambda: tables)
    monkeypatch.setattr(mod.tempfile, "mkdtemp", make_staging)
    monkeypatch.setitem(
        sys.modules,
        "huggingface_hub",
        SimpleNamespace(HfApi=api, hf_hub_download=download),
    )

    mod.main()

    make_staging.assert_called_once()
    api.assert_not_called()
    download.assert_not_called()
    assert {path.name for path in staging.iterdir()} == {
        f"{name}.parquet" for name in tables
    }
    for name, expected in tables.items():
        actual = pd.read_parquet(staging / f"{name}.parquet")
        pd.testing.assert_frame_equal(actual, expected)
    assert "dry-run: nothing uploaded" in capsys.readouterr().out
