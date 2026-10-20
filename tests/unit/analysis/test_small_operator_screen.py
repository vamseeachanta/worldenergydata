"""Independent arithmetic checks for the descriptive operator screen.

All policy thresholds and dates below are synthetic test inputs, not field
acceptance limits. The worked rates use January, February and March 2024
(calendar lengths 31, 29 and 31 days). Expected results are calculated here
by hand; no expected value is obtained from a screen helper.
"""

import copy
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from worldenergydata.analysis.small_operator_screen.screen import run_screen
from worldenergydata.analysis.small_operator_screen.validation import validate_cases

SIGNALS = ("underperformance", "decline", "step_change", "idle", "erratic")


def config():
    """Synthetic policy: three months, two peers, equal unit signal weights."""
    return {
        "as_of": "2024-03",
        "history_months": 3,
        "min_operator_wells": 1,
        "max_operator_wells": 10,
        "peer_group": {"vintage_years": 5, "depth_band_ft": None},
        "sensitivity_peer_group": {"vintage_years": 1, "depth_band_ft": 1000},
        "min_peers": 2,
        "thresholds": {
            "underperformance": 0.4,
            "decline": 0.3,
            "step_change": 0.3,
            "idle": 1,
            "erratic": 0.2,
        },
        "min_prior_rate_bopd": 1,
        "weights": dict.fromkeys(SIGNALS, 1),
        "concentration_weight": 1,
        "policy_source": "Synthetic arithmetic example in test docstrings, 2026",
        "validation": {"min_recall": 1, "max_false_positive_rate": 0},
    }


def well(key, rates, operator="op-a", field="f-a", vintage=2020, depth=2000):
    """Volumes = independently chosen calendar daily rates times day counts."""
    return {
        "well_key": key,
        "operator_no": operator,
        "field_key": field,
        "first_production_year": vintage,
        "depth_ft": depth,
        "production_basis": "well",
        "source": "Synthetic monthly records, 2026",
        "production": [
            {"month": month, "oil_bbl": rate * days}
            for month, days, rate in zip(
                ("2024-01", "2024-02", "2024-03"), (31, 29, 31), rates
            )
        ],
    }


def inputs():
    return {
        "registry": [
            {"operator_no": "op-a", "well_count_total": 1, "source": "Synthetic"},
            {"operator_no": "op-b", "well_count_total": 2, "source": "Synthetic"},
        ],
        "wells": [
            well("a", [10, 5, 2]),
            well("b", [10, 10, 10], "op-b"),
            well("c", [10, 10, 10], "op-b"),
        ],
    }


def target(result, key="a"):
    return next(row for row in result["wells"] if row["well_key"] == key)


def test_peer_signals_and_operator_explanation():
    """a: deficit 1-2/10=.8; decline 1-2/10=.8; max step=1-2/5=.6.

    Peers b,c have zero decline, step and CV. a's mean=17/3; sum of
    squared deviations=98/3; sample variance=49/3, CV=7/(sqrt(3)*17/3).
    Four signals exceed the supplied thresholds: score=4. One field gives
    HHI=1 squared=1; op-a score=mean(4)+1*1=5.
    """
    result = run_screen(inputs(), config())
    row = target(result)
    assert row["signals"]["underperformance"]["value"] == pytest.approx(0.8)
    assert row["signals"]["decline"]["value"] == pytest.approx(0.8)
    assert row["signals"]["step_change"]["value"] == pytest.approx(0.6)
    assert row["signals"]["erratic"]["value"] == pytest.approx(
        7 / (math.sqrt(3) * (17 / 3))
    )
    assert row["signals"]["underperformance"]["peer_count"] == 2
    assert row["score"] == 4
    assert row["candidate"] is True
    assert row["cause_status"] == "UNRESOLVED"
    assert "depletion" in row["cause_note"]
    operator = result["operators"][0]
    assert operator["operator_no"] == "op-a"
    assert operator["score"] == 5
    assert operator["concentration"]["hhi"] == 1
    assert operator["mean_well_score"] == 4
    assert result["validation"]["status"] == "NOT_EVALUATED"
    assert result["validation"]["false_positive_rate"] is None


def test_idle_prior_rate_and_time_and_missing_month():
    """Rates 10,0,0 give two observed idle months, prior rate 10.

    A missing February is not an idle observation or a contiguous decline.
    """
    data = inputs()
    data["wells"][0] = well("a", [10, 0, 0])
    row = target(run_screen(data, config()))
    assert row["signals"]["idle"]["value"] == 2
    assert row["signals"]["idle"]["prior_rate_bopd"] == 10
    assert row["signals"]["idle"]["triggered"]
    del data["wells"][0]["production"][1]
    row = target(run_screen(data, config()))
    assert row["signals"]["idle"]["status"] == "NOT_EVALUATED"
    assert row["signals"]["decline"]["status"] == "NOT_EVALUATED"
    assert row["signals"]["erratic"]["status"] == "NOT_EVALUATED"


def test_peer_sensitivity_and_target_exclusion():
    """Broad group has two peers; narrow vintage leaves a without peers."""
    data = inputs()
    data["wells"][1]["first_production_year"] = 2021
    data["wells"][2]["first_production_year"] = 2021
    row = target(run_screen(data, config()))
    assert row["signals"]["underperformance"]["peer_count"] == 2
    assert row["sensitivity"]["signals"]["underperformance"]["status"] == (
        "NOT_EVALUATED"
    )
    assert row["sensitivity"]["score_delta"] == -4
    assert row["sensitivity"]["candidate_changed"] is True


def test_pressure_is_context_with_provenance_and_no_score():
    """Pressure 100/2000=.05 is preserved as context, never an uplift score."""
    data = inputs()
    data["pressure"] = [
        {
            "api14": "a",
            "test_date": "2024-02-01",
            "pressure_psia": 100,
            "pressure_kind": "BHP_measured",
            "reference_depth_ft": 2000,
            "source_file": "Synthetic pressure table",
        },
        {
            "api14": "a",
            "test_date": "2025-01-01",
            "pressure_psia": 999,
            "pressure_kind": "BHP_measured",
            "reference_depth_ft": 2000,
            "source_file": "Synthetic future observation",
        },
    ]
    result = run_screen(data, config())
    row = target(result)
    assert row["pressure"]["pressure_psia"] == 100
    assert row["pressure"]["gradient_psi_ft"] == 0.05
    assert row["pressure"]["source_file"] == "Synthetic pressure table"
    assert row["score"] == 4
    data["pressure"][0]["pressure_kind"] = "WHP_shut_in"
    assert target(run_screen(data, config()))["pressure"]["gradient_psi_ft"] is None


def test_lease_totals_excluded_and_large_operators_still_supply_peers():
    """Peer pool includes operators above the selection band; leases do not."""
    data = inputs()
    data["registry"][1]["well_count_total"] = 100
    result = run_screen(data, config())
    assert [row["operator_no"] for row in result["operators"]] == ["op-a"]
    assert target(result)["signals"]["underperformance"]["peer_count"] == 2
    data["wells"][0]["production_basis"] = "lease"
    result = run_screen(data, config())
    assert not result["wells"]
    assert result["excluded"][0]["reason"] == "production_not_attributed_to_well"
    assert result["operators"][0]["status"] == "NOT_EVALUATED"
    assert result["operators"][0]["score"] is None


def test_hhi_uses_inventory_and_reports_partial_coverage():
    """Two supplied wells in distinct fields: HHI=.5²+.5²=.5.

    Registered inventory is four, so observed coverage=2/4=.5 and this HHI
    describes only the supplied inventory, never the entire registry.
    """
    data = inputs()
    data["registry"][0]["well_count_total"] = 4
    data["wells"].append(well("d", [10, 10, 10], field="f-b"))
    operator = next(
        row
        for row in run_screen(data, config())["operators"]
        if row["operator_no"] == "op-a"
    )
    assert operator["concentration"]["hhi"] == 0.5
    assert operator["inventory_coverage"] == 0.5
    assert operator["concentration"]["basis"] == "supplied_well_inventory"


def test_reproducible_order_and_inputs_not_mutated():
    """Reversing input order leaves every rank and evidence value unchanged."""
    data, settings = inputs(), config()
    original = copy.deepcopy((data, settings))
    first = run_screen(data, settings)
    assert (data, settings) == original
    data["wells"].reverse()
    data["registry"].reverse()
    assert run_screen(data, settings) == first
    json.dumps(first, allow_nan=False)


@pytest.mark.parametrize("history_months", [2.0, 3.0])
def test_integral_numeric_lookback_preserves_caller_policy(history_months):
    """Integral JSON numbers define whole months without changing the caller.

    Rates (10,5,2) give a fractional decline of .6 over two months and .8
    over three months. The output retains a normalized integer lookback.
    """
    settings = config()
    settings["history_months"] = history_months
    original = copy.deepcopy(settings)
    result = run_screen(inputs(), settings)
    expected_decline = 0.6 if history_months == 2 else 0.8
    assert target(result)["signals"]["decline"]["value"] == pytest.approx(
        expected_decline
    )
    assert type(result["config"]["history_months"]) is int
    assert json.dumps(settings, sort_keys=True) == json.dumps(original, sort_keys=True)
    assert type(settings["history_months"]) is float


def test_integral_numeric_policy_fields_are_normalized_without_mutation():
    """Whole-number policy inputs retain integer semantics, including groups."""
    settings = config()
    for field in (
        "history_months",
        "min_operator_wells",
        "max_operator_wells",
        "min_peers",
    ):
        settings[field] = float(settings[field])
    settings["peer_group"]["vintage_years"] = 5.0
    settings["sensitivity_peer_group"]["vintage_years"] = 1.0
    settings["thresholds"]["idle"] = 1.0
    original = json.dumps(settings, sort_keys=True)
    result = run_screen(inputs(), settings)
    retained = result["config"]
    assert type(retained["history_months"]) is int
    assert type(retained["min_operator_wells"]) is int
    assert type(retained["max_operator_wells"]) is int
    assert type(retained["min_peers"]) is int
    assert type(retained["peer_group"]["vintage_years"]) is int
    assert type(retained["sensitivity_peer_group"]["vintage_years"]) is int
    assert type(retained["thresholds"]["idle"]) is int
    assert target(result)["peer_group"] == ["f-a", 404, None]
    assert type(target(result)["peer_group"][1]) is int
    assert target(result)["score"] == 4
    assert json.dumps(settings, sort_keys=True) == original


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="Additional ISO formats require Python 3.11."
)
@pytest.mark.parametrize(
    "older,newer",
    [
        ("20240101", "2024-02-01"),
        ("2024-01-01", "20240201"),
        ("2024-W01-1", "2024-02-01"),
        ("20240101", "2024-W05-4"),
        ("20240203", "2024-02-15"),
    ],
)
def test_pressure_mixed_iso_dates_select_latest_observation(older, newer):
    """The later dated 200 psia observation wins across accepted ISO formats."""
    data = inputs()
    data["pressure"] = [
        {
            "api14": "a",
            "test_date": tested,
            "pressure_psia": pressure,
            "pressure_kind": "BHP_measured",
            "reference_depth_ft": 2000,
            "source_file": "Synthetic pressure table",
        }
        for tested, pressure in ((older, 100), (newer, 200), ("20240401", 999))
    ]
    original = copy.deepcopy(data)
    result = run_screen(data, config())
    context = target(result)["pressure"]
    assert context["test_date"] == newer
    assert context["pressure_psia"] == 200
    assert context["gradient_psi_ft"] == 0.1
    assert target(result)["score"] == 4
    assert data == original
    data["pressure"].reverse()
    assert run_screen(data, config()) == result


@pytest.mark.skipif(
    sys.version_info < (3, 11), reason="Additional ISO formats require Python 3.11."
)
def test_pressure_equivalent_dates_keep_deterministic_tie_breakers():
    """Equal dates use record values before date spelling, in either order."""
    data = inputs()
    data["pressure"] = [
        {
            "api14": "a",
            "test_date": tested,
            "pressure_psia": pressure,
            "pressure_kind": "BHP_measured",
            "source_file": "Synthetic pressure table",
        }
        for tested, pressure in (("20240201", 100), ("2024-02-01", 200))
    ]
    result = run_screen(data, config())
    assert target(result)["pressure"]["pressure_psia"] == 200
    assert target(result)["pressure"]["test_date"] == "2024-02-01"
    data["pressure"].reverse()
    assert run_screen(data, config()) == result
    data["pressure"].append({**data["pressure"][0], "test_date": "20240201"})
    result = run_screen(data, config())
    assert target(result)["pressure"]["test_date"] == "20240201"
    data["pressure"].reverse()
    assert run_screen(data, config()) == result


def test_pressure_equal_numeric_values_have_stable_json_output():
    """Equal int/float pressures retain the same JSON representation on reversal."""
    data = inputs()
    data["pressure"] = [
        {
            "api14": "a",
            "test_date": "2024-02-01",
            "pressure_psia": pressure,
            "pressure_kind": "BHP_measured",
            "source_file": "Synthetic pressure table",
        }
        for pressure in (100, 100.0)
    ]
    result = run_screen(data, config())
    assert target(result)["pressure"]["pressure_psia"] == 100
    data["pressure"].reverse()
    assert json.dumps(run_screen(data, config()), sort_keys=True) == json.dumps(
        result, sort_keys=True
    )


@pytest.mark.parametrize(
    "change", ["duplicate_well", "duplicate_month", "negative", "nan"]
)
def test_bad_observations_rejected(change):
    """Duplicate identity/months and invalid volumes cannot be ranked."""
    data = inputs()
    if change == "duplicate_well":
        data["wells"].append(copy.deepcopy(data["wells"][0]))
    elif change == "duplicate_month":
        data["wells"][0]["production"].append(data["wells"][0]["production"][0])
    else:
        data["wells"][0]["production"][0]["oil_bbl"] = (
            -1 if change == "negative" else float("nan")
        )
    with pytest.raises(ValueError):
        run_screen(data, config())


@pytest.mark.parametrize(
    "field", ["min_peers", "weights", "policy_source", "thresholds"]
)
def test_policy_has_no_hidden_defaults(field):
    """Every policy quantity is explicitly supplied and traceable."""
    settings = config()
    del settings[field]
    with pytest.raises(ValueError):
        run_screen(inputs(), settings)


def test_zero_history_and_missing_current_are_not_candidates():
    """All-zero peers cannot define a fractional deficit; missing is not zero."""
    data = inputs()
    data["wells"] = [well(key, [0, 0, 0]) for key in ("a", "b", "c")]
    data["registry"] = [data["registry"][0]]
    data["registry"][0]["well_count_total"] = 3
    row = target(run_screen(data, config()))
    assert not row["candidate"]
    assert row["signals"]["underperformance"]["status"] == "NOT_EVALUATED"
    assert row["signals"]["idle"]["status"] == "NOT_EVALUATED"
    data["wells"][0]["production"].pop()
    row = target(run_screen(data, config()))
    assert row["status"] == "NOT_EVALUATED"


def test_validation_counts_and_missing_evidence():
    """Hand matrix: TP=1,FN=1,FP=1,TN=1; recall=.5, FPR=.5."""
    rows = [
        {"well_key": key, "candidate": selected, "status": "EVALUATED"}
        for key, selected in zip(("a", "b", "c", "d"), (True, False, True, False))
    ]
    cases = [
        {"well_key": key, "known_good": good, "source": "Synthetic hand matrix"}
        for key, good in zip(("a", "b", "c", "d"), (True, True, False, False))
    ]
    gate = validate_cases(rows, cases, config()["validation"])
    assert gate["recall"] == 0.5
    assert gate["false_positive_rate"] == 0.5
    assert gate["status"] == "FAIL"
    assert gate["counts"] == {"tp": 1, "fn": 1, "fp": 1, "tn": 1}
    cases[0]["source"] = ""
    assert validate_cases(rows, cases, config()["validation"])["status"] == (
        "NOT_EVALUATED"
    )
    assert validate_cases(rows, [], config()["validation"])["status"] == (
        "NOT_EVALUATED"
    )


def test_validation_does_not_turn_missing_controls_into_zero_fpr():
    """A sole recovered positive gives recall=1 but leaves FPR undefined."""
    row = {"well_key": "a", "candidate": True, "status": "EVALUATED"}
    case = {"well_key": "a", "known_good": True, "source": "Synthetic"}
    gate = validate_cases([row], [case], config()["validation"])
    assert gate["recall"] == 1
    assert gate["false_positive_rate"] is None
    assert gate["status"] == "NOT_EVALUATED"


def test_cli_writes_example_and_nonzero_validation_status(tmp_path):
    """The shipped example runs; missing real analogs do not pass its gate."""
    example = Path("examples/analysis/small_operator_screen.json")
    output = tmp_path / "screen.json"
    command = [
        sys.executable,
        "-m",
        "worldenergydata.analysis.small_operator_screen",
        "--input",
        str(example),
        "--output",
        str(output),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    assert completed.returncode == 2
    result = json.loads(output.read_text())
    assert result["validation"]["status"] == "NOT_EVALUATED"
    assert target(result)["score"] == 4
    assert result["input_sha256"]


def test_cli_accepts_integral_numeric_lookback(tmp_path):
    """The shipped JSON example accepts 3.0 months and retains its gate status."""
    example = Path("examples/analysis/small_operator_screen.json")
    payload = json.loads(example.read_text())
    payload["config"]["history_months"] = 3.0
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    raw = json.dumps(payload)
    source.write_text(raw)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "worldenergydata.analysis.small_operator_screen",
            "--input",
            str(source),
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2, completed.stderr
    result = json.loads(output.read_text())
    assert result["config"]["history_months"] == 3
    assert type(result["config"]["history_months"]) is int
    assert result["validation"]["status"] == "NOT_EVALUATED"
    assert target(result)["score"] == 4
    assert source.read_text() == raw


def test_missing_peer_depth_does_not_pool_unknown_depths():
    """A depth-sensitive group has no comparable members without known depth."""
    data = inputs()
    data["wells"][0]["depth_ft"] = None
    result = run_screen(data, config())
    row = target(result)
    assert row["sensitivity"]["peer_group"] is None
    assert row["sensitivity"]["signals"]["underperformance"]["peer_count"] == 0


def test_future_production_cannot_change_scores():
    """Future volumes are validated but excluded from the historical cutoff."""
    data = inputs()
    first = run_screen(data, config())
    data["wells"][0]["production"].append({"month": "2024-04", "oil_bbl": 99999})
    assert run_screen(data, config()) == first


@pytest.mark.parametrize(
    "field,value",
    [
        ("min_peers", 0),
        ("history_months", 1),
        ("min_operator_wells", 2.5),
        ("concentration_weight", float("inf")),
        ("policy_source", " "),
    ],
)
def test_invalid_policy_rejected(field, value):
    """Mathematical domains, not empirical acceptance limits, are enforced."""
    settings = config()
    settings[field] = value
    with pytest.raises(ValueError):
        run_screen(inputs(), settings)


def test_weight_zero_disables_candidacy():
    """No enabled signal means score zero and no candidate."""
    settings = config()
    settings["weights"] = dict.fromkeys(SIGNALS, 0)
    row = target(run_screen(inputs(), settings))
    assert row["score"] == 0
    assert row["candidate"] is False


def test_idle_ties_use_prior_rate_then_shorter_idle():
    """With only idle weighted: b prior=20 beats a prior=10; c beats a
    at equal prior=10 because c has one idle month and a has two.
    """
    data = inputs()
    data["wells"] = [
        well("a", [10, 0, 0]),
        well("b", [20, 0, 0], "op-b"),
        well("c", [10, 10, 0], "op-b"),
    ]
    settings = config()
    settings["weights"] = dict.fromkeys(SIGNALS, 0)
    settings["weights"]["idle"] = 1
    assert [row["well_key"] for row in run_screen(data, settings)["wells"]] == [
        "b",
        "c",
        "a",
    ]


def test_missing_vintage_excluded_and_inventory_mismatch_rejected():
    """Missing peer metadata is explicit; conflicting inventory fails input."""
    data = inputs()
    data["wells"][0]["first_production_year"] = None
    result = run_screen(data, config())
    assert result["excluded"] == [
        {"well_key": "a", "reason": "missing_field_or_vintage"}
    ]
    data = inputs()
    data["registry"][1]["well_count_total"] = 1
    with pytest.raises(ValueError, match="exceeds registry"):
        run_screen(data, config())


def test_validation_pass_missing_well_and_duplicate():
    """TP=1,TN=1 gives recall=1,FPR=0; unknown case cannot pass."""
    rows = [
        {"well_key": "a", "candidate": True, "status": "EVALUATED"},
        {"well_key": "b", "candidate": False, "status": "EVALUATED"},
    ]
    cases = [
        {"well_key": "a", "known_good": True, "source": "Synthetic positive"},
        {"well_key": "b", "known_good": False, "source": "Synthetic control"},
    ]
    assert validate_cases(rows, cases, config()["validation"])["status"] == "PASS"
    cases[1]["well_key"] = "missing"
    assert validate_cases(rows, cases, config()["validation"])["status"] == (
        "NOT_EVALUATED"
    )
    cases[1]["well_key"] = "a"
    with pytest.raises(ValueError, match="duplicate"):
        validate_cases(rows, cases, config()["validation"])


def test_cli_success_and_failed_gate(tmp_path):
    """The same hand labels pass or fail without suppressing the JSON output."""
    payload = {"data": inputs(), "config": config()}
    payload["data"]["validation_cases"] = [
        {"well_key": "a", "known_good": True, "source": "Synthetic positive"},
        {"well_key": "b", "known_good": False, "source": "Synthetic control"},
    ]
    source, output = tmp_path / "input.json", tmp_path / "output.json"
    command = [
        sys.executable,
        "-m",
        "worldenergydata.analysis.small_operator_screen",
        "--input",
        str(source),
        "--output",
        str(output),
    ]
    source.write_text(json.dumps(payload))
    assert subprocess.run(command, capture_output=True, check=False).returncode == 0
    assert json.loads(output.read_text())["validation"]["status"] == "PASS"
    payload["data"]["validation_cases"][1]["known_good"] = True
    source.write_text(json.dumps(payload))
    assert subprocess.run(command, capture_output=True, check=False).returncode == 2
    payload["data"]["validation_cases"][0]["known_good"] = False
    source.write_text(json.dumps(payload))
    assert subprocess.run(command, capture_output=True, check=False).returncode == 1
    assert json.loads(output.read_text())["validation"]["status"] == "FAIL"


@pytest.mark.parametrize("citation", [" ", 42, False])
def test_validation_requires_text_citation(citation):
    """Whitespace and nontext values cannot stand in for a public citation."""
    rows = [
        {"well_key": "a", "candidate": True, "status": "EVALUATED"},
        {"well_key": "b", "candidate": False, "status": "EVALUATED"},
    ]
    cases = [
        {"well_key": "a", "known_good": True, "source": citation},
        {"well_key": "b", "known_good": False, "source": "Synthetic control"},
    ]
    assert validate_cases(rows, cases, config()["validation"])["status"] == (
        "NOT_EVALUATED"
    )


def test_output_policy_is_snapshot():
    """The retained policy describes the run even if the caller edits config."""
    settings = config()
    result = run_screen(inputs(), settings)
    settings["weights"]["underperformance"] = 99
    assert result["config"]["weights"]["underperformance"] == 1


def test_unevaluated_wells_sort_last():
    """With one peer required, b and c evaluate while a has no current rate."""
    data = inputs()
    data["wells"][0]["production"].pop()
    settings = config()
    settings["min_peers"] = 1
    result = run_screen(data, settings)
    assert result["wells"][-1]["well_key"] == "a"
    assert result["wells"][-1]["status"] == "NOT_EVALUATED"
