"""Selection and exit contracts for the standalone refresh CLI.

Interface citation: ``scripts/refresh_bsee_all.py`` argument help describes
``--dir``, ``--skip-ogor``, ``--dry-run``, ``--force`` and the default of four
workers; its usage example supplies the explicit two-worker input below.
Synthetic inputs enumerate two regular and two OGOR sentinels in interleaved
order. Expected selections are listed independently of registry implementation.
Exit code one denotes an unsuccessful CLI invocation; normal return denotes
success. These tests exercise dispatch only, without download or data writes.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, sentinel

import pytest

# File ancestry: bsee, unit, tests, repository root.
REPO_ROOT = Path(__file__).resolve().parents[3]
REGISTRY_MODULE = "worldenergydata.bsee.data.refresh.url_registry"


@pytest.fixture
def cli(monkeypatch, tmp_path):
    monkeypatch.syspath_prepend(str(REPO_ROOT / "scripts"))
    import refresh_bsee_all
    import requests
    import workspace_bootstrap

    forbidden = Mock(side_effect=AssertionError("HTTP or pool startup is forbidden"))
    monkeypatch.setattr(requests.sessions.Session, "request", forbidden)
    monkeypatch.setattr(refresh_bsee_all, "_get_requests", forbidden)
    monkeypatch.setattr(refresh_bsee_all, "ThreadPoolExecutor", forbidden)
    monkeypatch.setattr(
        refresh_bsee_all.BSEERefreshOrchestrator, "_run_pool", forbidden
    )

    bootstrap = Mock()
    monkeypatch.setattr(workspace_bootstrap, "bootstrap_workspace", bootstrap)
    monkeypatch.setattr(refresh_bsee_all, "_find_project_root", lambda: tmp_path)

    registry = ModuleType(REGISTRY_MODULE)
    registry.DatasetSpec = sentinel.dataset_spec_type
    registry.get_all_specs = Mock(
        side_effect=lambda: iter(
            (sentinel.regular_z, sentinel.ogor_b, sentinel.regular_a, sentinel.ogor_a)
        )
    )
    registry.get_regular_specs = Mock(
        side_effect=lambda: iter((sentinel.regular_z, sentinel.regular_a))
    )
    registry.get_ogor_a_specs = Mock(
        side_effect=AssertionError("CLI must use the selected registry entry point")
    )
    registry.get_specs_for_dir = Mock(
        side_effect=lambda name: (
            [sentinel.ogor_b, sentinel.ogor_a] if name == "yearly" else []
        )
    )
    monkeypatch.setitem(sys.modules, REGISTRY_MODULE, registry)

    state = SimpleNamespace(
        module=refresh_bsee_all,
        root=tmp_path,
        registry=registry,
        constructor_calls=[],
        refresh_calls=[],
        summary_calls=[],
        results=[],
    )

    class RecordingOrchestrator:
        run_tag = "synthetic"

        def __init__(self, **kwargs):
            state.constructor_calls.append(kwargs)

        def refresh_all(self, specs):
            state.refresh_calls.append(specs)
            return state.results

        def print_summary(self, results):
            state.summary_calls.append(results)

    monkeypatch.setattr(
        refresh_bsee_all, "BSEERefreshOrchestrator", RecordingOrchestrator
    )

    def invoke(*arguments):
        monkeypatch.setattr(sys, "argv", ["refresh_bsee_all.py", *arguments])
        return refresh_bsee_all.main()

    state.invoke = invoke
    yield state

    forbidden.assert_not_called()
    bootstrap.assert_called_once_with(tmp_path)
    registry.get_ogor_a_specs.assert_not_called()
    assert list(tmp_path.iterdir()) == []


def _assert_dispatch(cli, expected_specs, *, dry_run=False, force=False, workers=4):
    assert cli.constructor_calls == [
        {
            "project_root": cli.root,
            "workers": workers,
            "dry_run": dry_run,
            "force": force,
        }
    ]
    assert cli.refresh_calls == [expected_specs]
    assert cli.summary_calls == [cli.results]
    (summarized_results,) = cli.summary_calls
    assert summarized_results is cli.results


def test_dir_precedes_skip_ogor(cli):
    assert cli.invoke("--dir", "yearly", "--skip-ogor", "--dry-run", "--force") is None
    _assert_dispatch(cli, [sentinel.ogor_b, sentinel.ogor_a], dry_run=True, force=True)
    cli.registry.get_specs_for_dir.assert_called_once_with("yearly")
    cli.registry.get_regular_specs.assert_not_called()
    cli.registry.get_all_specs.assert_not_called()


def test_unknown_dir_exits_before_refresh(cli, caplog):
    with pytest.raises(SystemExit) as exc:
        cli.invoke("--dir", "missing", "--skip-ogor")
    assert exc.value.code == 1
    assert "No specs found for directory 'missing'" in caplog.text
    assert cli.constructor_calls == []
    assert cli.refresh_calls == []
    assert cli.summary_calls == []
    cli.registry.get_specs_for_dir.assert_called_once_with("missing")
    cli.registry.get_regular_specs.assert_not_called()
    cli.registry.get_all_specs.assert_not_called()


FLAG_CASES = [
    pytest.param((), False, False, 4, id="defaults"),
    pytest.param(
        ("--dry-run", "--force", "--workers", "2"), True, True, 2, id="explicit"
    ),
    pytest.param(("--force",), False, True, 4, id="force-without-dry-run"),
]


@pytest.mark.parametrize("arguments,dry_run,force,workers", FLAG_CASES)
def test_full_selection(cli, arguments, dry_run, force, workers):
    assert cli.invoke(*arguments) is None
    _assert_dispatch(
        cli,
        [sentinel.regular_z, sentinel.ogor_b, sentinel.regular_a, sentinel.ogor_a],
        dry_run=dry_run,
        force=force,
        workers=workers,
    )
    cli.registry.get_all_specs.assert_called_once_with()
    cli.registry.get_regular_specs.assert_not_called()
    cli.registry.get_specs_for_dir.assert_not_called()


@pytest.mark.parametrize("arguments,dry_run,force,workers", FLAG_CASES)
def test_regular_only_selection(cli, arguments, dry_run, force, workers):
    assert cli.invoke("--skip-ogor", *arguments) is None
    _assert_dispatch(
        cli,
        [sentinel.regular_z, sentinel.regular_a],
        dry_run=dry_run,
        force=force,
        workers=workers,
    )
    cli.registry.get_regular_specs.assert_called_once_with()
    cli.registry.get_all_specs.assert_not_called()
    cli.registry.get_specs_for_dir.assert_not_called()


@pytest.mark.parametrize(
    "statuses,exit_code",
    [
        pytest.param(("success",), None, id="success"),
        pytest.param(("skipped",), None, id="skipped"),
        pytest.param(("success", "skipped"), None, id="success-and-skipped"),
        pytest.param(("failed", "skipped", "success"), 1, id="failed-first"),
        pytest.param(("skipped", "failed", "success"), 1, id="failed-middle"),
        pytest.param(("success", "skipped", "failed"), 1, id="failed-last"),
    ],
)
def test_result_status_controls_exit(cli, statuses, exit_code):
    cli.results = [SimpleNamespace(status=status) for status in statuses]
    if exit_code is None:
        assert cli.invoke() is None
    else:
        with pytest.raises(SystemExit) as exc:
            cli.invoke()
        assert exc.value.code == exit_code
    _assert_dispatch(
        cli,
        [sentinel.regular_z, sentinel.ogor_b, sentinel.regular_a, sentinel.ogor_a],
    )
