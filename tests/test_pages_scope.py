"""Pages scope examples derived by enumerating changed inputs, without rendering.

The expected selections follow the input ownership in scripts/build_pages.py
and the conservative fallback required by issue #528. No engineering quantities
or acceptance thresholds are calculated here.
"""

import importlib.util
import os
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "pages_scope.py"
WORKFLOW = ROOT / ".github" / "workflows" / "pages.yml"
KNOWN = ("lower_tertiary", "hse", "marine_safety", "capabilities")


@pytest.fixture
def scope():
    spec = importlib.util.spec_from_file_location("pages_scope", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "paths, expected",
    [
        (["reports/hse/card.html"], (False, ["hse"])),
        (
            ["reports/hse/card.html", "reports/lower_tertiary/report.md"],
            (False, ["lower_tertiary", "hse"]),
        ),
        (["reports/hse/a.html", "reports/hse/b.html"], (False, ["hse"])),
        (["reports/lower_tertiary_field_summary.md"], (False, ["lower_tertiary"])),
        (["reports/lower_tertiary_field_summary.md.json"], (False, ["lower_tertiary"])),
        (["reports/IMO_GISIS_Executive_Report.html"], (False, ["marine_safety"])),
        (
            ["docs/intervention-db/intervention-stats-brief.html"],
            (False, ["capabilities"]),
        ),
        (["reports/unknown/card.html"], (True, [])),
        (["reports/hse/card.html", "reports/unknown/card.html"], (True, [])),
        (["reports/hse-adjacent/card.html"], (True, [])),
        (["README.md"], (False, [])),
        ([], (False, [])),
    ],
)
def test_path_ownership(scope, paths, expected):
    """Union the enumerated owners; any unowned report requires all builders."""
    assert scope.select_domains([("M", path) for path in paths], KNOWN) == expected


@pytest.mark.parametrize(
    "path",
    [
        "scripts/build_pages.py",
        "scripts/pages_scope.py",
        "scripts/site_nav.py",
        "scripts/lower_tertiary/war_methodology.py",
        "config/nav_spine.json",
        ".github/workflows/pages.yml",
        "site_assets/shared.html",
    ],
)
def test_shared_dependencies_require_full_build(scope, path):
    """Each listed input supplies shared presentation or selection behavior."""
    assert scope.select_domains([("M", path)], KNOWN) == (True, [])


@pytest.mark.parametrize("status", ["D", "T"])
def test_removed_or_retyped_input_requires_clean_build(scope, status):
    """A copied report's absent old output cannot survive a clean build."""
    assert scope.select_domains([(status, "reports/hse/old.html")], KNOWN) == (
        True,
        [],
    )


def test_rename_requires_clean_build(scope):
    """With rename detection disabled, a move has a removed and an added path."""
    changes = [("D", "reports/hse/old.html"), ("A", "reports/hse/new.html")]
    assert scope.select_domains(changes, KNOWN) == (True, [])


def test_registry_can_extend_without_changing_selector(scope):
    assert scope.select_domains(
        [("A", "reports/new_domain/index.html")], ["new_domain"]
    ) == (
        False,
        ["new_domain"],
    )


def test_null_delimited_git_diff_preserves_unusual_filenames(scope, monkeypatch):
    """One newline-bearing filename remains one owned input, not two paths."""
    calls = []

    def git_run(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(
            command, 0, stdout=b"M\0reports/hse/a\nwith space.html\0", stderr=b""
        )

    monkeypatch.setattr(scope.subprocess, "run", git_run)
    assert scope.revision_scope("before", "after", KNOWN) == (False, ["hse"])
    assert "--no-renames" in calls[0]
    assert "-z" in calls[0]


def test_unavailable_diff_requires_full_build(scope, monkeypatch):
    def missing_revision(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr(scope.subprocess, "run", missing_revision)
    assert scope.revision_scope("missing", "HEAD", KNOWN) == (True, [])
    assert scope.revision_scope("", "HEAD", KNOWN) == (True, [])


@pytest.mark.parametrize("event", ["workflow_dispatch", "push"])
def test_cli_without_base_requires_full_build(event):
    result = subprocess.run(
        ["python", str(SCRIPT), "--event", event],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "full=true\ndomains=\n"


def test_cli_unchanged_revision_selects_no_domains():
    result = subprocess.run(
        ["python", str(SCRIPT), "--base", "HEAD", "--head", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "full=false\ndomains=\n"


def test_manual_dispatch_with_valid_history_still_rebuilds_all():
    result = subprocess.run(
        [
            "python",
            str(SCRIPT),
            "--event",
            "workflow_dispatch",
            "--base",
            "HEAD",
            "--head",
            "HEAD",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout == "full=true\ndomains=\n"


@pytest.fixture
def workflow():
    return yaml.safe_load(WORKFLOW.read_text())


def test_workflow_restores_only_exact_predecessor(workflow):
    """The diff base and cached source revision must be identical (issue #528)."""
    steps = workflow["jobs"]["build"]["steps"]
    scope_step = next(step for step in steps if step.get("id") == "scope")
    restore = next(step for step in steps if "/cache/restore@" in step.get("uses", ""))
    save = next(step for step in steps if "/cache/save@" in step.get("uses", ""))
    build = next(
        step for step in steps if step.get("name") == "Build static site (stdlib only)"
    )
    assert scope_step["env"]["BEFORE"] == "${{ github.event.before }}"
    assert scope_step["env"]["AFTER"] == "${{ github.sha }}"
    assert "--base" in scope_step["run"]
    assert restore["id"] == "tree"
    assert restore["with"]["key"] == "pages-public-v2-${{ github.event.before }}"
    assert "restore-keys" not in restore["with"]
    assert save["with"]["key"] == "pages-public-v2-${{ github.sha }}"
    assert build["env"] == {
        "FULL_REBUILD": "${{ steps.scope.outputs.full }}",
        "CACHE_HIT": "${{ steps.tree.outputs.cache-hit }}",
        "DOMAINS": "${{ steps.scope.outputs.domains }}",
    }


@pytest.mark.parametrize(
    "full, hit, domains, expected",
    [
        ("false", "true", "hse", ["--domains", "hse"]),
        ("false", "true", "hse,capabilities", ["--domains", "hse,capabilities"]),
        ("false", "true", "", ["--domains", ""]),
        ("false", "false", "hse", ["--clean"]),
        ("false", "", "hse", ["--clean"]),
        ("true", "true", "hse", ["--clean"]),
    ],
)
def test_workflow_build_branches(workflow, tmp_path, full, hit, domains, expected):
    """Enumerate shell branches: only an exact cache hit permits partial output.

    Expected argument lists are literal CLI invocations from the issue's build
    contract. A recording executable replaces Python, so the actual workflow
    shell is exercised without writing generated pages into the repository.
    """
    steps = workflow["jobs"]["build"]["steps"]
    build = next(
        step for step in steps if step.get("name") == "Build static site (stdlib only)"
    )
    recorder = tmp_path / "python"
    recorder.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$ARGUMENTS"\n')
    recorder.chmod(0o755)  # POSIX executable fixture; no engineering threshold.
    arguments = tmp_path / "arguments.txt"
    env = dict(
        os.environ,
        PATH=str(tmp_path) + os.pathsep + os.environ["PATH"],
        ARGUMENTS=str(arguments),
        FULL_REBUILD=full,
        CACHE_HIT=hit,
        DOMAINS=domains,
    )
    subprocess.run(["bash", "-c", build["run"]], env=env, check=True)
    assert arguments.read_text().splitlines() == ["scripts/build_pages.py", *expected]


def test_workflow_triggers_cover_shared_inputs(workflow, scope):
    # PyYAML's YAML 1.1 reader treats the Actions `on` key as boolean True.
    triggers = workflow[True]["push"]["paths"]
    for path in scope.SHARED_FILES:
        assert path in triggers
    assert "site_assets/**" in triggers
    assert "docs/intervention-db/intervention-stats-brief.html" in triggers
