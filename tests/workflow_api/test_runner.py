# ABOUTME: TDD for worldenergydata.workflow_api.run_workflow (workspace-hub#3286).
# ABOUTME: envelope shape + side-effect-freeness + wed code_version + engine embed signature.

"""Tests for the wed deterministic workflow runner."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLE_OUTPUTS = (
    REPO_ROOT / "examples" / "workflows" / "bsee-production-summary" / "outputs"
)


def _dir_snapshot(path: Path) -> dict:
    snap = {}
    if path.exists():
        for p in sorted(path.rglob("*")):
            if p.is_file():
                snap[str(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return snap


def test_run_workflow_wed_returns_envelope():
    from assetutilities.workflow_api import ResultEnvelope

    from worldenergydata.workflow_api import run_workflow

    env = run_workflow("bsee-production-summary")
    assert isinstance(env, ResultEnvelope)
    assert env.status == "ok", env.warnings
    assert env.result["kind"] == "files"
    assert len(env.result["outputs"]) >= 1
    # wed stamps its OWN package version, never assetutilities'
    assert env.provenance["code_version"]["package_version"] is not None
    assert env.determinism["result_hash"] is not None
    assert env.determinism["reproducible"] is None  # not requested


def test_run_workflow_writes_nothing_outside_tempdir():
    from worldenergydata.workflow_api import run_workflow

    before = _dir_snapshot(EXAMPLE_OUTPUTS)
    run_workflow("bsee-production-summary")
    after = _dir_snapshot(EXAMPLE_OUTPUTS)
    assert before == after, "embed run mutated the committed example outputs dir"


def test_run_workflow_unknown_id_error_envelope():
    from worldenergydata.workflow_api import run_workflow

    env = run_workflow("does-not-exist")
    assert env.status == "error"
    assert env.warnings
    assert "does-not-exist" in env.warnings[0]


def test_run_workflow_excludes_save_cfg_dump():
    """The save_cfg <file_name>.yml dump is excluded from the payload."""
    from worldenergydata.workflow_api import run_workflow

    env = run_workflow("bsee-production-summary")
    basenames = [o["basename"] for o in env.result["outputs"]]
    # the cfg dump is named "<file_name>.yml"; no bare cfg-dump .yml in payload
    yml_dumps = [b for b in basenames if b.endswith(".yml")]
    assert yml_dumps == [], f"save_cfg dump leaked into payload: {yml_dumps}"


def test_run_workflow_result_hash_stable_across_runs():
    """Two independent embed runs (different tempdirs) hash identically."""
    from worldenergydata.workflow_api import run_workflow

    h1 = run_workflow("bsee-production-summary").determinism["result_hash"]
    h2 = run_workflow("bsee-production-summary").determinism["result_hash"]
    assert h1 == h2


def test_engine_embed_calls_configure_embed_without_library_name():
    """engine(embed=True) calls configure_embed POSITIONALLY, no library_name."""
    from unittest.mock import patch

    import worldenergydata.engine as engine_mod

    captured = {}
    real_cls = engine_mod.ConfigureApplicationInputs

    class _SpyCAI(real_cls):
        def configure_embed(self, cfg, basename, root_folder, log_to_file=False):
            captured["args"] = (cfg, basename, root_folder)
            captured["log_to_file"] = log_to_file
            # short-circuit: raise to stop the heavy router after capture
            raise RuntimeError("stop-after-capture")

    cfg = {"basename": "bsee", "data": {"groups": []}}
    with patch.object(engine_mod, "ConfigureApplicationInputs", _SpyCAI):
        with pytest.raises(RuntimeError, match="stop-after-capture"):
            engine_mod.engine(
                cfg=dict(cfg),
                embed=True,
                root_folder="/tmp/wed_embed_probe",
                log_to_file=False,
            )

    assert "args" in captured
    _, basename, root_folder = captured["args"]
    # basename is the 2nd positional (NOT library_name); root the 3rd
    assert basename == "bsee"
    assert root_folder == "/tmp/wed_embed_probe"
    assert captured["log_to_file"] is False


def test_engine_embed_requires_root_folder():
    from worldenergydata.engine import engine

    with pytest.raises(ValueError, match="root_folder"):
        engine(cfg={"basename": "bsee"}, embed=True, root_folder=None)
