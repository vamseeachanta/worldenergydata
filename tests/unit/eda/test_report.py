"""Independent fixtures for the evidence-only EDA report; no EDA tool is run."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts/eda/report.py"
spec = importlib.util.spec_from_file_location("eda_report", SCRIPT)
report = importlib.util.module_from_spec(spec)
spec.loader.exec_module(report)

# Python 3 hashlib documentation, Usage example (retrieved 2026-10-19):
# https://docs.python.org/3/library/hashlib.html#usage
HASH_INPUT = b"Nobody inspects the spammish repetition"
HASH_EXPECTED = "031edd7d41651593c5fe5c006fa5752b37fddff7bc4e843aa6af0c950f4b9406"


def manifest(tmp_path, **updates):
    data = {"provenance": {}, "artifacts": {}, "observations": {}}
    data.update(updates)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_missing_evidence_never_passes(tmp_path):
    text = report.build_report(manifest(tmp_path))
    for category in ("Timing", "Area", "Power", "DRC", "LVS"):
        assert f"| {category} | NOT_EVALUATED |" in text
    for artifact in (
        "rtl",
        "config",
        "metrics",
        "timing",
        "power",
        "drc",
        "lvs",
        "def",
        "gds",
        "log",
    ):
        assert f"| {artifact} | NOT_EVALUATED |" in text
    assert "PASS" not in text
    assert "No flow was executed" in text
    assert "Revision history" in text


def test_published_digest_and_replay_are_deterministic(tmp_path):
    """Expected SHA-256 is the published Python hashlib Usage vector above."""
    (tmp_path / "design.v").write_bytes(HASH_INPUT)
    path = manifest(
        tmp_path, artifacts={"rtl": {"path": "design.v", "sha256": HASH_EXPECTED}}
    )
    first = report.build_report(path)
    assert HASH_EXPECTED in first
    assert "| rtl | PRESENT |" in first
    assert first == report.build_report(path)


def test_digest_mismatch_is_a_hard_error(tmp_path):
    (tmp_path / "design.v").write_bytes(HASH_INPUT + b"changed")
    path = manifest(
        tmp_path, artifacts={"rtl": {"path": "design.v", "sha256": HASH_EXPECTED}}
    )
    with pytest.raises(ValueError, match="digest mismatch: rtl"):
        report.build_report(path)


def test_metrics_are_reported_with_exact_key_unit_and_basis(tmp_path):
    """Hand calculation: slack = required - arrival = 12.0 - 14.5 = -2.5 ns.

    OpenLane Newcomers, STA (rolling docs, retrieved 2026-10-19) explains
    required/actual arrival and negative slack. These are synthetic test inputs,
    not measured silicon results; no acceptance threshold is inferred.
    https://openlane2.readthedocs.io/en/latest/getting_started/newcomers/index.html#sta
    """
    (tmp_path / "metrics.json").write_text('{"example_setup_slack": -2.5}')
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "timing": {
                "key": "example_setup_slack",
                "unit": "ns",
                "basis": "synthetic hand calculation",
            }
        },
    )
    text = report.build_report(path)
    assert "| Timing | REPORTED | -2.5 ns |" in text
    assert "example_setup_slack" in text
    assert "synthetic hand calculation" in text
    assert "| LVS | NOT_EVALUATED |" in text
    assert "PASS" not in text


@pytest.mark.parametrize("value", [0, -2.5, 12.0])
def test_finite_values_including_zero_are_preserved(tmp_path, value):
    """Literal serialization cases, not engineering constants or limits."""
    (tmp_path / "metrics.json").write_text(json.dumps({"test": value}))
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "area": {"key": "test", "unit": "test-unit", "basis": "literal fixture"}
        },
    )
    assert f"REPORTED | {value} test-unit" in report.build_report(path)


@pytest.mark.parametrize(
    "value", [None, True, "0", [], {}, float("nan"), float("inf"), float("-inf")]
)
def test_invalid_metric_values_fail_closed(tmp_path, value):
    (tmp_path / "metrics.json").write_text(json.dumps({"test": value}))
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "drc": {"key": "test", "unit": "count", "basis": "literal fixture"}
        },
    )
    with pytest.raises(ValueError):
        report.build_report(path)


def test_missing_metric_key_is_not_evaluated(tmp_path):
    (tmp_path / "metrics.json").write_text("{}")
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "power": {"key": "absent", "unit": "W", "basis": "literal fixture"}
        },
    )
    assert "| Power | NOT_EVALUATED |" in report.build_report(path)


@pytest.mark.parametrize(
    "relative",
    [
        "../outside",
        "/absolute",
        "a/../../outside",
        "C:\\outside",
        "a\\b",
        "./design.v",
        "a//b",
    ],
)
def test_artifact_paths_are_confined(tmp_path, relative):
    path = manifest(tmp_path, artifacts={"rtl": {"path": relative}})
    with pytest.raises(ValueError, match="relative artifact path"):
        report.build_report(path)


def test_symlink_escape_is_rejected(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "outside.v"
    outside.write_bytes(HASH_INPUT)
    (root / "design.v").symlink_to(outside)
    path = manifest(root, artifacts={"rtl": {"path": "design.v"}})
    with pytest.raises(ValueError, match="escapes evidence root"):
        report.build_report(path)


@pytest.mark.parametrize(
    "content",
    [
        '{"provenance":{},"provenance":{}}',
        '{"artifacts": NaN}',
        '{"artifacts": Infinity}',
        '{"artifacts": -Infinity}',
        "[]",
    ],
)
def test_ambiguous_or_invalid_json_is_rejected(tmp_path, content):
    path = tmp_path / "manifest.json"
    path.write_text(content)
    with pytest.raises((TypeError, ValueError)):
        report.build_report(path)


@pytest.mark.parametrize(
    "updates",
    [
        {"extra": {}},
        {"artifacts": {"unknown": {"path": "a"}}},
        {"observations": {"timing": {"key": "test", "unit": "ns"}}},
        {"provenance": {"openlane_version": True}},
        {"artifacts": {"rtl": {"path": "a", "sha256": "bad"}}},
        {"observations": {"power": {"key": "test", "unit": "", "basis": "test"}}},
    ],
)
def test_schema_errors_are_rejected(tmp_path, updates):
    with pytest.raises(ValueError):
        report.build_report(manifest(tmp_path, **updates))


def test_table_text_is_escaped(tmp_path):
    text = report.build_report(
        manifest(tmp_path, provenance={"openlane_version": "<script>|`line\nnext"})
    )
    assert "<script>" not in text
    assert "&lt;script&gt;&#124;&#96;line next" in text


def test_cli_replays_committed_sample():
    sample = ROOT / "docs/examples/eda"
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(sample / "manifest.json")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout == (sample / "report.md").read_text(encoding="utf-8")


def test_cli_error_is_concise_and_emits_no_report(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(manifest(tmp_path, artifacts=[]))],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0
    assert result.stdout == ""
    assert "invalid evidence:" in result.stderr
    assert "Traceback" not in result.stderr


def test_hash_is_computed_without_expected_digest(tmp_path):
    """The same published hashlib vector must be inventoried without a hint."""
    (tmp_path / "input.v").write_bytes(HASH_INPUT)
    path = manifest(tmp_path, artifacts={"rtl": {"path": "input.v"}})
    assert HASH_EXPECTED in report.build_report(path)


def test_missing_expected_digest_is_an_integrity_error(tmp_path):
    path = manifest(
        tmp_path, artifacts={"rtl": {"path": "missing.v", "sha256": HASH_EXPECTED}}
    )
    with pytest.raises(ValueError, match="cannot verify expected digest"):
        report.build_report(path)


def test_directory_is_not_an_artifact(tmp_path):
    (tmp_path / "directory").mkdir()
    path = manifest(tmp_path, artifacts={"gds": {"path": "directory"}})
    with pytest.raises(ValueError, match="not a regular file"):
        report.build_report(path)


def test_relative_paths_do_not_depend_on_working_directory(tmp_path, monkeypatch):
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    (evidence / "input.v").write_bytes(HASH_INPUT)
    path = manifest(evidence, artifacts={"rtl": {"path": "input.v"}})
    monkeypatch.chdir(tmp_path)
    assert HASH_EXPECTED in report.build_report(path)


def test_absent_file_is_named_in_inventory(tmp_path):
    path = manifest(tmp_path, artifacts={"gds": {"path": "absent.gds"}})
    text = report.build_report(path)
    assert "| gds | NOT_EVALUATED | absent.gds (missing) | unavailable |" in text


def test_duplicate_metric_keys_are_rejected(tmp_path):
    (tmp_path / "metrics.json").write_text('{"test": 0, "test": 1}')
    path = manifest(tmp_path, artifacts={"metrics": {"path": "metrics.json"}})
    with pytest.raises(ValueError, match="duplicate JSON key"):
        report.build_report(path)


def test_nested_metric_data_is_not_flattened(tmp_path):
    (tmp_path / "metrics.json").write_text('{"corner": {"test": 0}}')
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "timing": {"key": "corner.test", "unit": "ns", "basis": "literal fixture"}
        },
    )
    assert "| Timing | NOT_EVALUATED |" in report.build_report(path)


def test_symlink_loop_produces_controlled_error(tmp_path):
    (tmp_path / "loop.v").symlink_to("loop.v")
    path = manifest(tmp_path, artifacts={"rtl": {"path": "loop.v"}})
    with pytest.raises(ValueError, match="invalid relative artifact path"):
        report.build_report(path)


def test_large_finite_exponent_is_preserved(tmp_path):
    """Literal JSON serialization case: exponent notation is a finite number."""
    (tmp_path / "metrics.json").write_text('{"test": 1e999}')
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "power": {"key": "test", "unit": "test-unit", "basis": "literal fixture"}
        },
    )
    assert "REPORTED | 1E+999 test-unit" in report.build_report(path)


@pytest.mark.parametrize("token", ["1e-999", "0.12345678901234567890123456789"])
def test_metric_decimal_precision_is_preserved(tmp_path, token):
    """Literal serialization inputs must survive without binary-float rounding.

    The expected exponent spelling differs only in case; the long fractional
    token is preserved verbatim. No physical coefficient or limit is used.
    """
    (tmp_path / "metrics.json").write_text('{"test": ' + token + "}")
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "timing": {"key": "test", "unit": "test-unit", "basis": "literal fixture"}
        },
    )
    assert f"REPORTED | {token.upper()} test-unit" in report.build_report(path)


def test_markdown_images_are_inert(tmp_path):
    text = report.build_report(
        manifest(tmp_path, provenance={"openlane_version": "![label](example)"})
    )
    assert "![label]" not in text


@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_unselected_nonfinite_metric_does_not_block_finite_evidence(tmp_path, token):
    (tmp_path / "metrics.json").write_text('{"selected": 0, "unused": ' + token + "}")
    path = manifest(
        tmp_path,
        artifacts={"metrics": {"path": "metrics.json"}},
        observations={
            "drc": {"key": "selected", "unit": "count", "basis": "literal fixture"}
        },
    )
    assert "| DRC | REPORTED | 0 count |" in report.build_report(path)


def test_cli_digest_error_names_artifact_without_echoing_path(tmp_path):
    (tmp_path / "private-input.v").write_bytes(b"changed")
    path = manifest(
        tmp_path,
        artifacts={"rtl": {"path": "private-input.v", "sha256": HASH_EXPECTED}},
    )
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "invalid evidence: digest mismatch: rtl" in result.stderr
    assert "private-input" not in result.stderr
    assert str(tmp_path) not in result.stderr


def test_cli_io_error_does_not_echo_path(tmp_path):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(tmp_path / "private-missing.json")],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "invalid evidence:" in result.stderr
    assert "private-missing" not in result.stderr
    assert str(tmp_path) not in result.stderr


def test_cli_decoding_error_does_not_echo_evidence(tmp_path):
    path = tmp_path / "private-input.json"
    path.write_bytes(b"\xff")
    result = subprocess.run(
        [sys.executable, str(SCRIPT), str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stdout == ""
    assert "invalid evidence:" in result.stderr
    assert "private-input" not in result.stderr
    assert "0xff" not in result.stderr
