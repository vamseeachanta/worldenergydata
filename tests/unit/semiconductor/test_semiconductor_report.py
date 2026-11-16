"""Offline report contracts using literal, manually enumerated expectations."""

import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from worldenergydata.semiconductor.__main__ import main


def test_catalog_report(capsys):
    """The catalog contains the curated role families and their proposed evidence."""
    assert main(["catalog"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["kind"] == "research_catalog"
    assert {role["id"] for role in report["roles"]} == {
        "physical_design",
        "layout_automation",
        "physical_verification",
        "packaging_thermal",
        "packaging_mechanical",
    }
    assert {skill["id"] for skill in report["skills"]} >= {
        "digital_flow",
        "layout_scripting",
        "design_rules",
        "heat_transfer",
        "thermal_stress",
    }
    assert report["sources"] and report["proposed_artifacts"]
    assert report["assessment"] == {
        "artifact_completion": "NOT_EVALUATED",
        "engineering_acceptance": "NOT_EVALUATED",
        "hiring_demand": "NOT_EVALUATED",
        "suitability": "NOT_EVALUATED",
    }


def test_match_report_has_reviewable_evidence_without_raw_input(monkeypatch, capsys):
    """DRC is the sole alias: select design_rules and its proposed report."""
    monkeypatch.setattr(sys, "stdin", io.StringIO("Synthetic private note: DRC"))
    assert main(["match"]) == 0
    raw = capsys.readouterr().out
    report = json.loads(raw)
    assert "Synthetic private note" not in raw
    assert report["kind"] == "keyword_evidence"
    assert report["matches"] == [
        {
            "role_id": "physical_verification",
            "hits": [{"skill_id": "design_rules", "keywords": ["drc"]}],
        }
    ]
    assert report["roles"][0]["artifact_ids"] == ["design_rule_report"]
    assert report["assessment"]["artifact_completion"] == "NOT_EVALUATED"
    assert raw.endswith("\n")


def test_empty_input_is_empty_evidence(monkeypatch, capsys):
    """Empty text has no aliases; it cannot select a default role."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    main(["match"])
    report = json.loads(capsys.readouterr().out)
    assert report["matches"] == []
    assert report["roles"] == []
    assert report["proposed_artifacts"] == []


def test_output_is_repeatable(monkeypatch, capsys):
    """Identical input yields identical JSON bytes with no timestamp or path."""
    outputs = []
    for text in ("OpenROAD and DRC", "OpenROAD and DRC"):
        monkeypatch.setattr(sys, "stdin", io.StringIO(text))
        main(["match"])
        outputs.append(capsys.readouterr().out)
    assert outputs[0] == outputs[1]


@pytest.mark.parametrize("args", [[], ["unknown"]])
def test_invalid_command(args):
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code != 0


@pytest.mark.parametrize("mode", ["catalog", "match"])
def test_module_entry_point_from_another_directory(mode, tmp_path):
    """The documented module command works without relying on the current folder."""
    root = Path(__file__).resolve().parents[3]
    result = subprocess.run(
        [sys.executable, "-m", "worldenergydata.semiconductor", mode],
        input="DRC",
        text=True,
        capture_output=True,
        check=True,
        cwd=tmp_path,
        env={**os.environ, "PYTHONPATH": str(root / "src")},
    )
    report = json.loads(result.stdout)
    assert report["kind"] == (
        "research_catalog" if mode == "catalog" else "keyword_evidence"
    )
    assert result.stderr == ""
