"""Pins for the per-well D&C listing (wo-april-2026-per-well-dc.md).

Locks the bore-level listing to the field-level reconciliation matrix in
wo-april-2026-validation.md section 3: same developments, same subtotals,
same 253-bore / 25,404-day universe.
"""

import importlib.util
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "lower_tertiary" / "build_wo_per_well_dc.py"
OUT_MD = REPO / "reports" / "lower_tertiary" / "wo-april-2026-per-well-dc.md"

# Development -> (bores, D&C days) exactly as published in the validation
# matrix (section 3) on the V50/wed basis.
MATRIX = {
    "Anchor": (17, 1825),
    "Buckskin": (25, 2056),
    "Cascade Chinook": (14, 2467),
    "Jack St Malo": (73, 7047),
    "Julia": (9, 1687),
    "Kaskida": (7, 841),
    "North Platte": (23, 971),
    "Shenandoah": (23, 2370),
    "Stones": (22, 2625),
    "Tiber": (2, 250),
    "Big Foot": (38, 3265),
}


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("build_wo_per_well_dc", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def devs(mod):
    return mod.load_bores()


def test_universe_pinned(devs):
    assert sum(len(b) for b in devs.values()) == 253
    assert (
        sum(b["drill"] + b["compl"] for bores in devs.values() for b in bores) == 25404
    )


def test_every_development_ties_to_matrix(devs):
    assert set(devs) == set(MATRIX)
    for dev, (bores, dc) in MATRIX.items():
        got_bores = len(devs[dev])
        got_dc = sum(b["drill"] + b["compl"] for b in devs[dev])
        assert (got_bores, got_dc) == (bores, dc), dev


def test_drill_completion_split_totals(devs):
    drill = sum(b["drill"] for bores in devs.values() for b in bores)
    compl = sum(b["compl"] for bores in devs.values() for b in bores)
    assert (drill, compl) == (12436, 12968)


def test_846_suspect_bores_flagged(devs):
    flagged = {b["api12"]: b["note"] for b in devs["Jack St Malo"] if b["note"]}
    assert set(flagged) == {"608124015400", "608124015504"}
    for note in flagged.values():
        assert "#846" in note


def test_producer_markers_join(devs):
    producers = sum(1 for bores in devs.values() for b in bores if b["producer"])
    assert producers == 56
    # Buckskin has no OGOR-A benchmark coverage — markers must be absent.
    assert not any(b["producer"] for b in devs["Buckskin"])


@pytest.fixture(scope="module")
def vintage(mod):
    return mod.load_vintage_diff()


def test_committed_markdown_is_regenerable(mod, devs, vintage):
    assert OUT_MD.exists(), "committed listing missing"
    assert mod.build_markdown(devs, vintage) == OUT_MD.read_text(encoding="utf-8")


def test_markdown_carries_matrix_numbers(devs):
    text = OUT_MD.read_text(encoding="utf-8")
    for needle in ("25,404", "12,436", "12,968", "| 73 | 73 |", "608124015504"):
        assert needle in text, needle


def test_drilling_days_stable_across_vintages(vintage):
    """The drilling-days resolution: no bore's drilling count ever changes."""
    assert "drilling_changed" not in vintage
    total = sum(len(rows) for rows in vintage.values())
    assert total == 253
    assert len(vintage["late_data"]) == 7
    assert len(vintage["servicing_accrual"]) == 5
    assert len(vintage["wed_only"]) == 36
    # Servicing accrual is completion-only by construction — assert anyway.
    assert all(int(r["d_drill"]) == 0 for r in vintage["servicing_accrual"])


def test_late_data_bores_include_846_suspects(vintage):
    apis = {r["api12"] for r in vintage["late_data"]}
    assert {"608124015400", "608124015504"} <= apis


def test_markdown_carries_resolution_section(devs):
    text = OUT_MD.read_text(encoding="utf-8")
    for needle in (
        "## Drilling-days resolution (frozen V30 → wed)",
        "Drilling days changed on 0 of 253 bores.",
        "Late-data bores",
        "Servicing accrual on long-TD'd bores",
    ):
        assert needle in text, needle
