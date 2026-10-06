"""Publication gate files must retain unambiguous JSON and raw byte evidence."""

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import catalog_test_support as support
import pytest

api = support.api
inputs = support.inputs
ROOT = Path(__file__).resolve().parents[3]
CLI = ROOT / "scripts/field_development/integrate_angola_catalog.py"


def load_cli():
    spec = importlib.util.spec_from_file_location("catalog_cli", CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_gate_json_rejects_duplicate_decisions(tmp_path):
    gate = tmp_path / "eligibility.json"
    gate.write_text('{"decision":"prohibited","decision":"permission_granted"}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_cli().optional_json(gate)


@pytest.mark.parametrize("constant", ["NaN", "Infinity", "-Infinity", "1e999"])
def test_nonstandard_numbers_are_rejected(api, constant):
    with pytest.raises(ValueError, match="non-finite JSON"):
        api.input_contract.strict_json(('{"cost":' + constant + "}").encode())


def test_cli_pins_raw_gate_input_bytes(inputs, tmp_path):
    gate = tmp_path / "eligibility.json"
    gate.write_bytes(b"[ ]\n")
    output = tmp_path / "result"
    subprocess.run(
        [
            sys.executable,
            "-I",
            str(CLI),
            "--snapshot",
            str(inputs[0]),
            "--legacy",
            str(inputs[1]),
            "--parent-costs",
            str(inputs[2]),
            "--eligibility",
            str(gate),
            "--output",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    manifest = json.loads((output / "integration_manifest.json").read_text("utf-8"))
    assert manifest["gate_input_sha256"] == {
        "eligibility": hashlib.sha256(gate.read_bytes()).hexdigest()
    }


@pytest.mark.parametrize("pins", [{"eligibility": "bad"}, {"unknown": "a" * 64}])
def test_invalid_raw_gate_input_pins_rejected(api, inputs, tmp_path, pins):
    bundle = api.build_integration(*inputs)
    bundle["manifest"]["gate_input_sha256"] = pins
    with pytest.raises(ValueError, match="digest|gate input"):
        api.write_bundle(bundle, tmp_path / "bad-pins")
