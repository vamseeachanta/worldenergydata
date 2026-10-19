"""Offline riser summary contract tests; no solver is imported or executed."""

import csv
import importlib.util
from pathlib import Path

import pytest

DEMO = Path(__file__).resolve().parents[3] / "scripts" / "demo"


def load_adapter():
    spec = importlib.util.spec_from_file_location(
        "_riser_results", DEMO / "_riser_results.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def summary(tmp_path):
    """Synthetic adapter inputs, not engineering evidence.

    Hand comparison: segment A life 80 yr < segment B life 120 yr; A governs.
    Required factored life is supplied as 100 yr: 80 < 100 therefore BELOW.
    No S-N calculation or standards-derived coefficient is exercised here.
    """
    path = tmp_path / "summary.csv"
    rows = [
        dict(
            segment_id="A", fatigue_life_years="80", wave_damage="0.2", viv_damage="0.1"
        ),
        dict(
            segment_id="B",
            fatigue_life_years="120",
            wave_damage="0.1",
            viv_damage="0.1",
        ),
    ]
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    return path


def test_imported_summary_uses_factored_life_and_minimum_segment(summary):
    result = load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")
    assert "80.0 yr" in result.headline
    assert "segment A" in result.headline
    assert "below" in result.headline
    assert "100.0-yr required factored life" in result.headline
    assert "Imported" in result.basis
    assert "Synthetic test criterion" in result.basis
    assert "LIVE" not in result.basis


@pytest.mark.parametrize("required", [80, 70])
def test_equality_and_above_meet_supplied_criterion(summary, required):
    """Hand comparison: 80 >= 80 and 80 >= 70 both meet the supplied criterion."""
    result = load_adapter().analysis_from_csv(
        summary, required, "Synthetic test criterion"
    )
    assert "meets" in result.headline


@pytest.mark.parametrize("required", [0, -1, float("nan"), float("inf")])
def test_invalid_criterion_rejected(summary, required):
    with pytest.raises(ValueError, match="required factored life"):
        load_adapter().analysis_from_csv(summary, required, "Synthetic test criterion")


def test_source_required(summary):
    with pytest.raises(ValueError, match="source"):
        load_adapter().analysis_from_csv(summary, 100, "  ")


@pytest.mark.parametrize(
    "field,value",
    [
        ("fatigue_life_years", "nan"),
        ("fatigue_life_years", "inf"),
        ("fatigue_life_years", "-1"),
        ("wave_damage", "-1"),
        ("viv_damage", "nan"),
        ("wave_damage", "bad"),
        ("segment_id", ""),
    ],
)
def test_invalid_result_is_rejected(summary, field, value):
    with summary.open() as stream:
        rows = list(csv.DictReader(stream))
    rows[1][field] = value
    with summary.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError):
        load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")


@pytest.mark.parametrize("contents", ["", "segment_id\n", "segment_id\nA\n"])
def test_empty_or_incomplete_csv_is_rejected(summary, contents):
    summary.write_text(contents)
    with pytest.raises(ValueError):
        load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")


def load_generator(monkeypatch):
    monkeypatch.syspath_prepend(str(DEMO))
    spec = importlib.util.spec_from_file_location(
        "riser_card", DEMO / "generate_riser_grounded_card.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generator_imports_summary_without_running_solver(
    summary, tmp_path, monkeypatch
):
    from worldenergydata.hse.grounding import ground

    generator = load_generator(monkeypatch)

    def forbidden():
        pytest.fail("Imported summary must never launch the live bridge")

    monkeypatch.setattr(generator, "build_live_analysis", forbidden)
    fixture = Path(__file__).parent / "fixtures" / "bsee_riser_pressure_sample.txt"
    monkeypatch.setattr(
        generator, "ground_and_log", lambda mode: ground(mode, bsee_path=fixture)
    )
    output = tmp_path / "card.html"
    assert (
        generator.main(
            [
                "--summary-csv",
                str(summary),
                "--required-life-years",
                "100",
                "--basis-source",
                "Synthetic test criterion",
                "--out",
                str(output),
            ]
        )
        == 0
    )
    html = output.read_text()
    assert "80.0 yr" in html
    assert "below" in html
    assert "NOT_EVALUATED" in html
    assert "CSV SHA-256" in html


@pytest.mark.parametrize(
    "arguments",
    [
        ["--summary-csv", "missing.csv"],
        ["--summary-csv", "missing.csv", "--required-life-years", "100"],
        ["--required-life-years", "100", "--basis-source", "Synthetic"],
        ["--summary-csv", "missing.csv", "--illustrative"],
    ],
)
def test_generator_rejects_incomplete_or_conflicting_modes(monkeypatch, arguments):
    with pytest.raises(SystemExit) as exc:
        load_generator(monkeypatch).main(arguments)
    assert exc.value.code == 2


def test_illustrative_panel_withholds_unsourced_design_life(monkeypatch):
    panel = load_generator(monkeypatch).ANALYSIS
    assert "NOT_EVALUATED" in panel.headline
    assert "25 yr" not in str(panel.metrics)


def test_duplicate_segment_rejected(summary):
    summary.write_text(summary.read_text().replace("B,120", "A,120"))
    with pytest.raises(ValueError, match="duplicate"):
        load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")


@pytest.mark.parametrize(
    "contents",
    [
        "segment_id,fatigue_life_years,wave_damage,viv_damage,wave_damage\nA,80,0.2,0.1,0.3\n",
        "segment_id,fatigue_life_years,wave_damage,viv_damage\nA,80,0.2,0.1,unexpected\n",
    ],
)
def test_ambiguous_csv_is_rejected(summary, contents):
    summary.write_text(contents)
    with pytest.raises(ValueError, match="Ambiguous"):
        load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")


def test_invalid_import_never_falls_back_or_writes_card(summary, tmp_path, monkeypatch):
    generator = load_generator(monkeypatch)
    summary.write_text("invalid summary")
    output = tmp_path / "card.html"
    with pytest.raises(ValueError):
        generator.main(
            [
                "--summary-csv",
                str(summary),
                "--required-life-years",
                "100",
                "--basis-source",
                "Synthetic test criterion",
                "--out",
                str(output),
            ]
        )
    assert not output.exists()
