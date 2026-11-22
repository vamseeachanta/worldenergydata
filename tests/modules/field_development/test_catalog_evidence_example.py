"""The runnable example is synthetic and leaves publication unresolved."""

import importlib.util
import json
import os
import subprocess
import sys

import pytest

from tests.modules.field_development import catalog_test_support as support

api = support.api


def example():
    path = support.ROOT / "scripts/field_development/example_catalog_evidence.py"
    spec = importlib.util.spec_from_file_location("example_catalog_evidence", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_example_counts_scopes_and_keeps_release_gated(api, tmp_path):
    """Hand count: one field + one phase + one development = three identities.

    One legacy field group remains pending. One field milestone keeps its upper
    date bound. Neither a development cost nor an inherited parent is invented.
    The inputs are authored synthetic records in the example, not research data.
    """
    result = example().run(tmp_path / "example")
    assert result == {
        "state": "local_draft_not_for_publication",
        "registered_fields": 1,
        "registered_nonfields": 2,
        "accepted_legacy_groups": 0,
        "field_record_groups": 2,
        "milestone_precision": "upper_bound_day",
        "source_urls": ["https://example.org/catalog-evidence"],
    }
    output = tmp_path / "example/bundle"
    bundle = api.read_bundle(output)
    assert all(row["decision"] == "unresolved" for row in bundle["eligibility"])
    with pytest.raises(ValueError, match="not a public dataset"):
        api.read_bundle(output, public_only=True)
    with pytest.raises(FileExistsError):
        example().run(tmp_path / "example")


def test_example_reaches_atlas_cli_only_as_explicit_preview(api, tmp_path):
    """One field and two nonfields survive CLI readback; public use is denied.

    These counts follow the same three authored identities as the hand count
    above. Independent authored inputs replace the withheld legacy catalog.
    """
    inputs_dir = tmp_path / "inputs"
    inputs_dir.mkdir()
    snapshot, legacy, parent = example().create_inputs(inputs_dir)
    legacy.write_text(
        "FIELD_ID,FIELD_NAME,COUNTRY,BLOCK,CURRENT_STATUS,RESERVE_TYPE,"
        "WATER_DEPTH_FT,US_GOM_FLAG\n"
        "example,Example field,Angola,,Discovery,Oil,100,\n",
        encoding="utf-8",
        newline="\n",
    )
    coverage = tmp_path / "coverage.csv"
    coverage.write_text("by_country,Angola,1,0\n", encoding="utf-8", newline="\n")
    roster = tmp_path / "roster.json"
    roster.write_text("[]", encoding="utf-8", newline="\n")
    scorecard = tmp_path / "scorecard.json"
    scorecard.write_text('{"modules": {}}', encoding="utf-8", newline="\n")
    directory = tmp_path / "bundle"
    api.write_bundle(api.build_integration(snapshot, legacy, parent), directory)
    cli = support.ROOT / "scripts/field_atlas/build_atlas_feed.py"
    output = tmp_path / "preview.json"
    # Invoke the real parser and generator with independent inputs; keep guards.
    bootstrap = """
import importlib.util
import sys
from pathlib import Path

script, fields, coverage, roster, scorecard, *arguments = sys.argv[1:]
sys.path.insert(0, str(Path(script).parent))
spec = importlib.util.spec_from_file_location("independent_feed", script)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
module.FIELDS_CSV = Path(fields)
module.COVERAGE_CSV = Path(coverage)
module.ROSTER = Path(roster)
module.SCORECARD = Path(scorecard)
sys.argv = [script, *arguments]
module.main()
"""
    command = [
        sys.executable,
        "-c",
        bootstrap,
        str(cli),
        str(legacy),
        str(coverage),
        str(roster),
        str(scorecard),
        "--catalog-extension",
        str(directory),
        "--output",
        str(output),
    ]
    env = os.environ.copy()
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_COMMON_DIR"):
        env.pop(name, None)
    denied = subprocess.run(
        command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        env=env,
        cwd=tmp_path,
    )
    assert denied.returncode != 0
    assert "not a public dataset" in denied.stderr
    assert not output.exists()
    subprocess.run(
        command + ["--research-preview"],
        check=True,
        capture_output=True,
        encoding="utf-8",
        env=env,
        cwd=tmp_path,
    )
    feed = json.loads(output.read_text(encoding="utf-8"))
    metadata = feed["meta"]["catalog_extension"]
    assert metadata["registered_fields"] == 1
    assert metadata["registered_nonfields"] == 2
    assert len(metadata["nonfield_entities"]) == 2
    row = next(r for r in feed["fields"] if r.get("source_dataset_id"))
    assert (
        row["research_evidence"]["sources"][0]["url"]
        == "https://example.org/catalog-evidence"
    )
    assert row["research_evidence"]["legacy_groups"] == []
