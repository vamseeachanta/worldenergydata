# ABOUTME: Regression tests: extractor outputs are re-opened by relative_path, not basename.
# ABOUTME: Two same-named files at different depths must keep distinct digests and bytes.
"""assetutilities' ``extract_result`` discovers outputs recursively and gives each a
POSIX ``relative_path`` from ``result_folder``. Re-opening outputs by ``basename``
gives a nested ``sub/README.md`` the digest (and bytes) of the top-level
``README.md``. Older extractor output has no ``relative_path``; then the basename
is the only key and must still work.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from worldenergydata.workflow_api import bsee_pilot
from worldenergydata.workflow_api import runner as R

TOP_BYTES = b"top-level readme\n"
NESTED_BYTES = b"nested readme, different bytes\n"


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_same_named_outputs(results: Path) -> None:
    (results / "sub").mkdir(parents=True)
    (results / "README.md").write_bytes(TOP_BYTES)
    (results / "sub" / "README.md").write_bytes(NESTED_BYTES)


def _payload() -> dict:
    # The shape assetutilities' extract_result emits for nested outputs.
    return {
        "kind": "files",
        "outputs": [
            {"basename": "README.md", "relative_path": "README.md", "sha256": _sha(TOP_BYTES)},
            {
                "basename": "README.md",
                "relative_path": "sub/README.md",
                "sha256": _sha(NESTED_BYTES),
            },
        ],
    }


def test_normalize_keeps_distinct_digests_for_same_named_outputs(tmp_path):
    results = tmp_path / "results"
    _write_same_named_outputs(results)
    payload = _payload()

    R._normalize_container_hashes(
        payload, {"Analysis": {"result_folder": str(results)}}, str(tmp_path)
    )

    digests = {o["relative_path"]: o["sha256"] for o in payload["outputs"]}
    assert digests == {
        "README.md": _sha(TOP_BYTES),
        "sub/README.md": _sha(NESTED_BYTES),
    }


def test_normalize_falls_back_to_basename_without_relative_path(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    (results / "out.csv").write_bytes(b"a,b\n1,2\n")
    payload = {"kind": "files", "outputs": [{"basename": "out.csv", "sha256": "stale"}]}

    R._normalize_container_hashes(
        payload, {"Analysis": {"result_folder": str(results)}}, str(tmp_path)
    )

    assert payload["outputs"][0]["sha256"] == _sha(b"a,b\n1,2\n")


def test_bsee_pilot_captures_bytes_per_relative_path(tmp_path, monkeypatch):
    results = tmp_path / "results"

    def fake_engine(cfg, embed, root_folder, log_to_file):
        _write_same_named_outputs(results)
        return {"Analysis": {"result_folder": str(results)}}

    monkeypatch.setattr("worldenergydata.engine.engine", fake_engine)
    monkeypatch.setattr(bsee_pilot, "extract_result", lambda *a, **k: (_payload(), []))
    monkeypatch.setattr(
        bsee_pilot.ResultLocator, "from_row", staticmethod(lambda row: object())
    )
    monkeypatch.setattr(
        R, "_resolve_wed_registry_row", lambda wid: {"input": "examples/x/input.yml"}
    )
    monkeypatch.setattr(R, "_build_wed_cfg", lambda row, params: {})
    monkeypatch.setattr(R, "_absolutize_input_paths", lambda cfg, d: cfg)
    config = {
        "snapshots": {"s": {"fixture": "f.csv", "query": {"area": "A", "block": 1}}}
    }

    payload, out_bytes = bsee_pilot.execute_variant("wf", ["0"], "g", "s", config)

    assert out_bytes == {"README.md": TOP_BYTES, "sub/README.md": NESTED_BYTES}
    digests = {o["relative_path"]: o["sha256"] for o in payload["outputs"]}
    assert digests["sub/README.md"] == _sha(NESTED_BYTES)


@pytest.mark.parametrize("rel", ["../escape.txt", "/abs.txt"])
def test_output_path_rejects_paths_outside_results(tmp_path, rel):
    with pytest.raises(ValueError):
        R._output_path(str(tmp_path), {"basename": "x", "relative_path": rel})
