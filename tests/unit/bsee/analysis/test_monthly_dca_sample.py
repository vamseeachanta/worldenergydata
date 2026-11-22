"""The sample is bounded, retains arrays and verifies its existing source owner."""

import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[4]
SPEC = importlib.util.spec_from_file_location(
    "build_bsee_dca_sample", ROOT / "scripts/bsee/build_dca_sample.py"
)
sample = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sample)


def test_sample_sources_fail_closed_after_tampering(tmp_path):
    source = ROOT / "data/economics/julia_life_to_date"
    replica = tmp_path / "dataset"
    shutil.copytree(source, replica)
    sample.load_sample(replica)
    path = replica / "raw/ogora2023.csv"
    original = path.read_bytes()
    before = hashlib.sha256(original).hexdigest()
    path.write_bytes(original + b"\n")
    tampered = hashlib.sha256(path.read_bytes()).hexdigest()
    assert tampered != before
    with pytest.raises(ValueError, match="digest"):
        sample.load_sample(replica)
    path.write_bytes(original)
    restored = hashlib.sha256(path.read_bytes()).hexdigest()
    assert restored == before
    sample.load_sample(replica)
    (tmp_path / "probe-evidence.json").write_text(
        json.dumps({"before": before, "tampered": tampered, "restored": restored}),
        encoding="utf-8",
    )
    assert (
        hashlib.sha256((source / "raw/ogora2023.csv").read_bytes()).hexdigest()
        == before
    )


def test_sample_three_cases_and_output_readback(tmp_path):
    manifest = sample.build(ROOT / "data/economics/julia_life_to_date", tmp_path)
    assert manifest["criteria_version"] == "bsee-dca-sample-v1"
    assert len(manifest["cases"]) == 3
    assert manifest["qa_status"] == "awaiting-owner-sample-review"
    for output in manifest["outputs"]:
        blob = (tmp_path / output["path"]).read_bytes()
        assert hashlib.sha256(blob).hexdigest() == output["sha256"]
        assert len(blob) == output["bytes"] < 5_000_000
    for case in manifest["cases"]:
        forecast = pd.read_csv(tmp_path / f"{case['slug']}-forecast.csv")
        assert forecast.cumulative_bbl.iloc[-1] == pytest.approx(
            case["observed_bbl"] + case["remaining_bbl"]
        )
        assert case["b"] <= 1
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    identifiers = re.findall(r'\bid="([^"]+)"', page)
    assert len(identifiers) == len(set(identifiers))
    assert "income = costs is not established" in page
    assert "SORT_NAME" not in page
    assert "awaiting-owner-sample-review" in json.dumps(manifest)
