"""Contracts for reviewing a candidate without replacing saved observations."""

from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest

AUDIT = Path(__file__).resolve().parents[3] / "scripts" / "audit"
sys.path.insert(0, str(AUDIT))


@pytest.fixture
def comparator():
    return importlib.import_module("compare_freshness_scorecard")


def scorecard(**fields):
    return {"modules": {"alpha": fields}}


def test_identical_inputs_are_unchanged(comparator):
    original = scorecard(record_count=0, last_refresh=None)
    snapshot = deepcopy(original)
    assert comparator.compare_scorecards(original, deepcopy(original)) == []
    assert original == snapshot


@pytest.mark.parametrize(
    ("before", "after", "before_present", "after_present", "old", "new"),
    [
        ({}, {"record_count": None}, False, True, None, None),
        ({"record_count": None}, {"record_count": 0}, True, True, None, 0),
        ({"record_count": 0}, {}, True, False, 0, None),
        ({"record_count": False}, {"record_count": 0}, True, True, False, 0),
        ({"values": [False]}, {"values": [0]}, True, True, [False], [0]),
        ({"record_count": 12}, {"record_count": 7}, True, True, 12, 7),
        (
            {"freshness_status": "fresh"},
            {"freshness_status": "missing"},
            True,
            True,
            "fresh",
            "missing",
        ),
    ],
)
def test_legacy_differences_preserve_presence_and_values(
    comparator, before, after, before_present, after_present, old, new
):
    field = next(iter(before or after))
    assert comparator.compare_scorecards(scorecard(**before), scorecard(**after)) == [
        {
            "path": f"/modules/alpha/{field}",
            "category": "legacy_value",
            "before_present": before_present,
            "after_present": after_present,
            "before": old,
            "after": new,
        }
    ]


def test_only_exact_fixture_field_has_fixture_category(comparator):
    before = {"fixture_readiness": "old", "modules": {"alpha": {}}}
    after = {
        "fixture_readiness": "new",
        "modules": {"alpha": {"fixture_readiness": "none", "record_count": 0}},
    }
    differences = comparator.compare_scorecards(before, after)
    assert [(d["path"], d["category"]) for d in differences] == [
        ("/fixture_readiness", "legacy_value"),
        ("/modules/alpha/fixture_readiness", "fixture_readiness"),
        ("/modules/alpha/record_count", "legacy_value"),
    ]
    assert differences[1] == {
        "path": "/modules/alpha/fixture_readiness",
        "category": "fixture_readiness",
        "before_present": False,
        "after_present": True,
        "before": None,
        "after": "none",
    }


def test_added_and_removed_modules_are_membership_changes(comparator):
    before = {"modules": {"removed": {"record_count": 2}}}
    after = {"modules": {"added": {"fixture_readiness": "packaged"}}}
    assert comparator.compare_scorecards(before, after) == [
        {
            "path": "/modules/added",
            "category": "module_membership",
            "before_present": False,
            "after_present": True,
            "before": None,
            "after": {"fixture_readiness": "packaged"},
        },
        {
            "path": "/modules/removed",
            "category": "module_membership",
            "before_present": True,
            "after_present": False,
            "before": {"record_count": 2},
            "after": None,
        },
    ]


def test_generation_metadata_is_visible_but_module_stamps_are_legacy(comparator):
    before = {
        "generated_at": "old",
        "report_date": "2026-06-08",
        "modules": {"alpha": {"generated_at": "old"}},
    }
    after = {
        "generated_at": "new",
        "report_date": "2026-06-09",
        "modules": {"alpha": {"generated_at": "new"}},
    }
    assert [
        (d["path"], d["category"]) for d in comparator.compare_scorecards(before, after)
    ] == [
        ("/generated_at", "generation_metadata"),
        ("/modules/alpha/generated_at", "legacy_value"),
        ("/report_date", "generation_metadata"),
    ]


def test_nested_fields_and_escaped_paths_are_deterministic(comparator):
    before = {"modules": {"a/b~c": {"details": {"z": 1, "a": [1, 2]}}}}
    after = {"modules": {"a/b~c": {"details": {"a": [2, 1], "z": 2}}}}
    snapshot = deepcopy((before, after))
    expected = [
        {
            "path": "/modules/a~1b~0c/details/a",
            "category": "legacy_value",
            "before_present": True,
            "after_present": True,
            "before": [1, 2],
            "after": [2, 1],
        },
        {
            "path": "/modules/a~1b~0c/details/z",
            "category": "legacy_value",
            "before_present": True,
            "after_present": True,
            "before": 1,
            "after": 2,
        },
    ]
    assert comparator.compare_scorecards(before, after) == expected
    assert comparator.compare_scorecards(before, after) == expected
    assert (before, after) == snapshot


@pytest.mark.parametrize(
    "invalid", [None, [], {}, {"modules": []}, {"modules": {"alpha": None}}]
)
def test_invalid_scorecard_shape_is_rejected(comparator, invalid):
    with pytest.raises(ValueError):
        comparator.compare_scorecards(invalid, {"modules": {}})
    with pytest.raises(ValueError):
        comparator.compare_scorecards({"modules": {}}, invalid)


def write_project(root):
    (root / "data").mkdir()
    (root / "module-manifest.yaml").write_text(
        "modules:\n  - id: alpha\n    catalog_status: not_applicable\n"
    )
    (root / "data/catalog.yaml").write_text("modules: {}\n")
    (root / "data/freshness-scorecard.json").write_text(json.dumps(scorecard()))


def snapshot(root):
    return {p.relative_to(root): p.read_bytes() for p in root.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    ("candidate", "code", "categories"),
    [
        (scorecard(), 0, []),
        (scorecard(fixture_readiness="none"), 0, ["fixture_readiness"]),
        ({**scorecard(), "generated_at": "new"}, 0, ["generation_metadata"]),
        ({**scorecard(), "report_date": "2026-06-08"}, 0, ["generation_metadata"]),
        (scorecard(record_count=0), 1, ["legacy_value"]),
        (
            {"modules": {"beta": {"fixture_readiness": "none"}, "alpha": {}}},
            1,
            ["module_membership"],
        ),
    ],
)
def test_cli_exit_contract_and_no_writes(
    comparator, tmp_path, monkeypatch, capsys, candidate, code, categories
):
    write_project(tmp_path)
    before = snapshot(tmp_path)
    calls = []

    def builder(root, report_date):
        calls.append((root, report_date))
        return candidate

    monkeypatch.setattr(comparator, "build_scorecard", builder)
    args = ["--project-root", str(tmp_path), "--date", "2026-06-08"]
    assert comparator.main(args) == code
    output = capsys.readouterr()
    assert output.err == ""
    differences = json.loads(output.out)
    assert [d["category"] for d in differences] == categories
    assert calls == [(tmp_path.resolve(), "2026-06-08")]
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize(
    ("file", "contents"),
    [
        ("data/freshness-scorecard.json", None),
        ("data/freshness-scorecard.json", "{"),
        ("data/freshness-scorecard.json", '{"modules": {}, "modules": {}}'),
        ("data/freshness-scorecard.json", '{"modules": {}, "value": NaN}'),
        ("data/freshness-scorecard.json", '{"modules": []}'),
        ("module-manifest.yaml", None),
        ("module-manifest.yaml", "modules: ["),
        ("module-manifest.yaml", "modules: {}"),
        ("module-manifest.yaml", "modules: !!int ''"),
        ("data/catalog.yaml", None),
        ("data/catalog.yaml", ""),
        ("data/catalog.yaml", "modules: []"),
        ("data/catalog.yaml", "modules: !!int ''"),
    ],
)
def test_cli_invalid_inputs_are_distinct_and_sanitized(
    comparator, tmp_path, capsys, file, contents
):
    write_project(tmp_path)
    target = tmp_path / file
    if contents is None:
        target.unlink()
    else:
        target.write_text(contents)
    before = snapshot(tmp_path)
    assert (
        comparator.main(["--project-root", str(tmp_path), "--date", "2026-06-08"]) == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    reason = "missing" if contents is None else "invalid"
    assert output.err == f"{file}: {reason} input\n"
    assert str(tmp_path) not in output.err
    assert snapshot(tmp_path) == before


def test_builder_failure_is_sanitized(comparator, tmp_path, monkeypatch, capsys):
    write_project(tmp_path)

    def fail(*args, **kwargs):
        raise ValueError(str(tmp_path / "private-input.json"))

    monkeypatch.setattr(comparator, "build_scorecard", fail)
    assert (
        comparator.main(["--project-root", str(tmp_path), "--date", "2026-06-08"]) == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert "candidate inputs: invalid local data" in output.err
    assert str(tmp_path) not in output.err


@pytest.mark.parametrize("report_date", ["invalid", "2026-02-30", "20260608"])
def test_invalid_date_is_sanitized(comparator, tmp_path, capsys, report_date):
    assert (
        comparator.main(["--project-root", str(tmp_path), "--date", report_date]) == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "--date: invalid report date\n"


@pytest.mark.parametrize("operation", ["resolve", "read_text"])
def test_unreadable_inputs_are_sanitized(
    comparator, tmp_path, monkeypatch, capsys, operation
):
    write_project(tmp_path)

    def denied(*args, **kwargs):
        raise PermissionError(str(tmp_path))

    monkeypatch.setattr(Path, operation, denied)
    assert (
        comparator.main(["--project-root", str(tmp_path), "--date", "2026-06-08"]) == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert "unreadable" in output.err
    assert str(tmp_path) not in output.err


def test_real_builder_empty_catalog_is_valid_and_offline(
    comparator, tmp_path, monkeypatch, capsys
):
    import socket

    write_project(tmp_path)
    fixture = tmp_path / "fixtures/synthetic.json"
    fixture.parent.mkdir()
    fixture.write_text('{"synthetic": true}\n')
    manifest = tmp_path / "module-manifest.yaml"
    manifest.write_text(
        manifest.read_text() + "    fixture_catalog: fixtures/synthetic.json\n"
    )
    candidate = comparator.build_scorecard(tmp_path, report_date="2026-06-08")
    saved = deepcopy(candidate)
    del saved["modules"]["alpha"]["fixture_readiness"]
    (tmp_path / "data/freshness-scorecard.json").write_text(json.dumps(saved))
    before = snapshot(tmp_path)

    def no_network(*args, **kwargs):
        pytest.fail("unexpected network access")

    monkeypatch.setattr(socket, "socket", no_network)
    assert (
        comparator.main(["--project-root", str(tmp_path), "--date", "2026-06-08"]) == 0
    )
    differences = json.loads(capsys.readouterr().out)
    fixture_change = next(
        d for d in differences if d["category"] == "fixture_readiness"
    )
    assert fixture_change["after"] == "packaged"
    assert all(
        d["category"] in {"fixture_readiness", "generation_metadata"}
        for d in differences
    )
    assert candidate["modules"]["alpha"]["freshness_status"] == "missing"
    assert candidate["modules"]["alpha"]["record_count"] == 0
    assert snapshot(tmp_path) == before


@pytest.mark.parametrize("module_id", ["caf\u00e9", "alpha"])
def test_utf8_inputs_with_utf8_mode_disabled(comparator, tmp_path, module_id):
    write_project(tmp_path)
    (tmp_path / "module-manifest.yaml").write_text(
        f"modules:\n  - id: {module_id}\n", encoding="utf-8"
    )
    (tmp_path / "data/catalog.yaml").write_text(
        f"modules:\n  {module_id}: {{}}\n", encoding="utf-8"
    )
    if module_id == "alpha":
        metadata = tmp_path / "data/modules/alpha/_metadata.json"
        metadata.parent.mkdir(parents=True)
        metadata.write_text('{"last_refresh": "r\u00e9cent"}', encoding="utf-8")
    saved = comparator.build_scorecard(tmp_path, report_date="2026-06-08")
    del saved["modules"][module_id]["fixture_readiness"]
    (tmp_path / "data/freshness-scorecard.json").write_text(
        json.dumps(saved), encoding="utf-8"
    )
    before = snapshot(tmp_path)
    env = dict(os.environ, LC_ALL="C", PYTHONCOERCECLOCALE="0")
    result = subprocess.run(
        [
            sys.executable,
            "-X",
            "utf8=0",
            str(AUDIT / "compare_freshness_scorecard.py"),
            "--project-root",
            str(tmp_path),
            "--date",
            "2026-06-08",
        ],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    differences = json.loads(result.stdout)
    assert [d for d in differences if d["category"] != "generation_metadata"] == [
        {
            "path": f"/modules/{module_id}/fixture_readiness",
            "category": "fixture_readiness",
            "before_present": False,
            "after_present": True,
            "before": None,
            "after": "none",
        }
    ]
    assert snapshot(tmp_path) == before


def test_script_entrypoint_from_another_directory(tmp_path):
    write_project(tmp_path)
    scripts = tmp_path / "scripts/audit"
    scripts.mkdir(parents=True)
    for name in ("compare_freshness_scorecard.py", "data_freshness_scorecard.py"):
        shutil.copyfile(AUDIT / name, scripts / name)
    before = snapshot(tmp_path)
    env = os.environ.copy()
    # Exercise the first invocation without inherited bytecode suppression.
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    env.pop("PYTHONPYCACHEPREFIX", None)
    result = subprocess.run(
        [
            sys.executable,
            str(scripts / "compare_freshness_scorecard.py"),
            "--project-root",
            str(tmp_path),
            "--date",
            "2026-06-08",
        ],
        cwd=tmp_path.parent,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert result.stderr == ""
    assert json.loads(result.stdout)
    assert snapshot(tmp_path) == before
