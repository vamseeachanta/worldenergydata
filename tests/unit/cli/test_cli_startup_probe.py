"""Independent arithmetic and failure cases for the startup evidence probe."""

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[3] / "scripts/audit/cli_startup_probe.py"


@pytest.fixture
def probe():
    spec = importlib.util.spec_from_file_location("cli_startup_probe", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_probe_records_timings_and_import_stack(probe, monkeypatch, tmp_path):
    """Hand calculation: elapsed = end - start; 11-10=1 and 22-20=2 seconds."""
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "probe",
            "--repeats",
            "2",
            "--timeout",
            "3",
            "--output",
            str(output),
            "--",
            "landman",
            "--help",
        ],
    )
    monkeypatch.setattr(probe.shutil, "which", lambda name: "worldenergydata")
    times = iter([10, 11, 20, 22])
    monkeypatch.setattr(probe.time, "perf_counter", lambda: next(times))
    calls = []

    def run(command, **kwargs):
        calls.append(command)
        assert kwargs["env"]["PYTHONPROFILEIMPORTTIME"] == "1"
        assert kwargs["timeout"] == 3
        return subprocess.CompletedProcess(command, 0, "help", "import stack")

    monkeypatch.setattr(probe.subprocess, "run", run)
    probe.main()
    evidence = json.loads(output.read_text())
    assert evidence["args"] == ["landman", "--help"]
    assert [sample["elapsed_seconds"] for sample in evidence["samples"]] == [1, 2]
    assert [sample["cache"] for sample in evidence["samples"]] == ["cold", "warm"]
    assert all(
        sample["import_stack"] == "import stack" for sample in evidence["samples"]
    )
    assert calls == [["worldenergydata", "landman", "--help"]] * 2


def test_probe_retains_timeout_evidence(probe, monkeypatch, tmp_path):
    output = tmp_path / "evidence.json"
    monkeypatch.setattr(
        "sys.argv",
        ["probe", "--repeats", "1", "--timeout", "1", "--output", str(output)],
    )
    monkeypatch.setattr(probe.shutil, "which", lambda name: "worldenergydata")

    def timeout(command, **kwargs):
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(probe.subprocess, "run", timeout)
    probe.main()
    sample = json.loads(output.read_text())["samples"][0]
    assert sample["timed_out"] is True
    assert sample["returncode"] is None


@pytest.mark.parametrize("value", ["0", "-1"])
def test_probe_rejects_nonpositive_inputs(probe, value):
    with pytest.raises(probe.argparse.ArgumentTypeError):
        probe.positive_int(value)
