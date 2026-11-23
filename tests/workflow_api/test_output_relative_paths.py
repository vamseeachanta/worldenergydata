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
            {
                "basename": "README.md",
                "relative_path": "README.md",
                "sha256": _sha(TOP_BYTES),
            },
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


@pytest.mark.parametrize(
    "rel",
    [
        "../escape.txt",  # parent segment
        "sub/../../escape.txt",  # parent segment after a real one
        "/abs.txt",  # rooted POSIX (not isabs on Windows + Python 3.13)
        "\\abs.txt",  # rooted Windows
        "C:evil.txt",  # drive-relative
        "C:/evil.txt",  # drive-absolute
        "//server/share/x.txt",  # UNC, POSIX spelling
        "\\\\server\\share\\x.txt",  # UNC, Windows spelling
        "sub\\x.txt",  # backslash: keys are POSIX; backslashes are rejected
        "sub//x.txt",  # empty segment
        "./x.txt",  # non-canonical segment
        "",  # empty key
    ],
)
def test_output_path_rejects_non_canonical_or_escaping_keys(tmp_path, rel):
    with pytest.raises(ValueError):
        R._output_path(str(tmp_path), {"basename": "x", "relative_path": rel})


def test_output_path_accepts_nested_posix_key(tmp_path):
    (tmp_path / "a" / "b").mkdir(parents=True)
    target = tmp_path / "a" / "b" / "c.csv"
    target.write_bytes(b"x")
    got = R._output_path(
        str(tmp_path), {"basename": "c.csv", "relative_path": "a/b/c.csv"}
    )
    assert Path(got) == target.resolve()


def test_output_path_rejects_symlink_escape(tmp_path):
    results = tmp_path / "results"
    results.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"secret")
    try:
        (results / "link.txt").symlink_to(outside)
    except (OSError, NotImplementedError) as exc:  # no symlink privilege (Windows)
        pytest.skip(f"symlinks unavailable: {exc}")
    with pytest.raises(ValueError):
        R._output_path(
            str(results), {"basename": "link.txt", "relative_path": "link.txt"}
        )


# --- curated labels follow the file NAME, identity stays the relative path ---


def test_build_outputs_labels_by_filename_not_relative_path():
    out_bytes = {
        "sub/prod_summ_example.csv": b"a,b\n1,2\n",  # nested primary result
        "prod_summ_archive/other.csv": b"c,d\n3,4\n",  # prefix only in the DIRECTORY
        "prod_summ_top.csv": b"e,f\n5,6\n",
    }
    config = {"algorithm": {"output_schema_version": "1"}}

    _artifacts, records, _objects, _xlsx = bsee_pilot.build_outputs(out_bytes, config)

    labels = {r["role"]: r["curated_label"] for r in records}
    assert labels == {
        "sub/prod_summ_example.csv": "primary_result",
        "prod_summ_archive/other.csv": "validation_evidence",
        "prod_summ_top.csv": "primary_result",
    }
