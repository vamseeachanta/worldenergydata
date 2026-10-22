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
    Consistent design life is 24 yr: 24 / (0.2 + 0.1) = 80 yr for A,
    and 24 / (0.1 + 0.1) = 120 yr for B, independently of the adapter.
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


def add_summary_columns(path, **columns):
    with path.open() as stream:
        rows = list(csv.DictReader(stream))
    for field, values in columns.items():
        for row, value in zip(rows, values):
            row[field] = value
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        writer.writerows(rows)


@pytest.mark.parametrize("row_index", [0, 1])
def test_imported_criterion_must_match_on_every_row(summary, row_index):
    criteria = ["25", "25"]
    criteria[row_index] = "240"
    add_summary_columns(summary, required_life_years=criteria)
    with pytest.raises(ValueError, match="required_life_years.*mismatch"):
        load_adapter().analysis_from_csv(summary, 25, "Synthetic test criterion")


@pytest.mark.parametrize("value", ["", "nan", "inf", "0", "-1", "bad"])
def test_invalid_imported_criterion_rejected(summary, value):
    add_summary_columns(summary, required_life_years=["100", value])
    with pytest.raises(ValueError, match="required_life_years"):
        load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")


def test_matching_imported_criterion_accepted_without_pass_column(summary):
    add_summary_columns(summary, required_life_years=["100", "100.0"])
    result = load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")
    assert "below" in result.headline


@pytest.mark.parametrize("with_criterion", [False, True])
@pytest.mark.parametrize(
    "required,passes", [(80, ["True", "True"]), (100, ["False", "True"])]
)
def test_consistent_imported_pass_column_accepted(
    summary, with_criterion, required, passes
):
    add_summary_columns(summary, passes_dff=passes)
    if with_criterion:
        add_summary_columns(summary, required_life_years=[required, required])
    result = load_adapter().analysis_from_csv(
        summary, required, "Synthetic test criterion"
    )
    assert ("meets" in result.headline) == (required == 80)


@pytest.mark.parametrize("with_criterion", [False, True])
@pytest.mark.parametrize("row_index", [0, 1])
def test_contradictory_imported_pass_rejected_on_every_row(
    summary, with_criterion, row_index
):
    passes = ["False", "True"]
    passes[row_index] = "True" if row_index == 0 else "False"
    add_summary_columns(summary, passes_dff=passes)
    if with_criterion:
        add_summary_columns(summary, required_life_years=["100", "100"])
    with pytest.raises(ValueError, match="passes_dff.*disagrees"):
        load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")


def test_false_imported_pass_at_equal_life_rejected(summary):
    add_summary_columns(summary, passes_dff=["False", "True"])
    with pytest.raises(ValueError, match="passes_dff.*disagrees"):
        load_adapter().analysis_from_csv(summary, 80, "Synthetic test criterion")


@pytest.mark.parametrize("value", ["", "yes", "1", "0", "nan"])
def test_invalid_imported_pass_rejected(summary, value):
    add_summary_columns(summary, passes_dff=["False", value])
    with pytest.raises(ValueError, match="passes_dff"):
        load_adapter().analysis_from_csv(summary, 100, "Synthetic test criterion")


@pytest.mark.parametrize(
    "life,required",
    [
        (79.96, 80),
        (80, 80.04),
        (80.04, 80),
        (79.99999999999999, 80),
        (1e-20, 2e-20),
        (1000.01, 1000.02),
    ],
)
def test_displayed_lives_preserve_the_comparison(summary, life, required):
    add_summary_columns(summary, fatigue_life_years=[life, life * 2])
    result = load_adapter().analysis_from_csv(
        summary, required, "Synthetic test criterion"
    )
    life_label = result.metrics[0][0].removesuffix(" yr")
    required_label = result.metrics[3][0].removesuffix(" yr")
    displayed_life = float(life_label.replace(",", ""))
    displayed_required = float(required_label.replace(",", ""))
    assert (displayed_life < displayed_required) == (life < required)
    assert displayed_life != displayed_required
    relation = "below" if life < required else "meets"
    assert f"Minimum fatigue life {life_label} yr" in result.headline
    assert f"{relation} the {required_label}-yr" in result.headline


def test_summary_help_states_infinite_life_rejects_whole_import(monkeypatch, capsys):
    with pytest.raises(SystemExit) as exc:
        load_generator(monkeypatch).main(["--help"])
    assert exc.value.code == 0
    help_text = " ".join(capsys.readouterr().out.split())
    assert (
        "Nonfinite life (including zero-damage infinite life) rejects the entire import."
        in help_text
    )


@pytest.mark.parametrize("column", ["required_life_years", "passes_dff"])
def test_contradictory_import_never_runs_solver_or_writes_card(
    summary, tmp_path, monkeypatch, column
):
    values = ["240", "240"] if column == "required_life_years" else ["True", "True"]
    add_summary_columns(summary, **{column: values})
    generator = load_generator(monkeypatch)

    def forbidden():
        pytest.fail("Contradictory import must never launch the live bridge")

    monkeypatch.setattr(generator, "build_live_analysis", forbidden)
    output = tmp_path / "card.html"
    with pytest.raises(ValueError, match=column):
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
