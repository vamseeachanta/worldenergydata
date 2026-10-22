"""Offline dataset tests; all field identities and values below are synthetic."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts/hf_export/build_field_development_dataset.py"
SOURCE = Path("reports/field_development/bsee_matched/_summary.json")


def exporter():
    spec = importlib.util.spec_from_file_location("field_development_dataset", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sample():
    """Hand calculation: 3 rows, 2 known actuals, 1 match; rate = 1/2 = 0.5.

    Row C lacks ground truth; its match is unknown, rather than false.
    The definition follows portfolio_matched.PortfolioRow.is_match / summarize.
    """
    return {
        "fields": [
            {
                "name": "Example C",
                "block": "XX3",
                "actual": None,
                "recommended": "spar",
                "match": None,
            },
            {
                "name": "Example B",
                "block": "XX2",
                "actual": "tlp",
                "recommended": "spar",
                "match": False,
            },
            {
                "name": "Example A",
                "block": "XX1",
                "actual": "spar",
                "recommended": "spar",
                "match": True,
            },
        ],
        "n_total": 3,
        "n_with_actual": 2,
        "n_matched": 1,
        "top1_match_rate": 0.5,
    }


def write_source(root, data):
    path = root / SOURCE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_build_projects_only_declared_columns_and_retains_unknown(tmp_path):
    data = sample()
    data["fields"][0]["unapproved_note"] = "excluded"
    write_source(tmp_path, data)
    files = exporter().build_dataset(tmp_path)
    rows = [json.loads(line) for line in files["matched_concepts.jsonl"].splitlines()]
    assert rows == [
        {
            "field_name": "Example A",
            "block": "XX1",
            "actual": "spar",
            "recommended": "spar",
            "match": True,
        },
        {
            "field_name": "Example B",
            "block": "XX2",
            "actual": "tlp",
            "recommended": "spar",
            "match": False,
        },
        {
            "field_name": "Example C",
            "block": "XX3",
            "actual": None,
            "recommended": "spar",
            "match": None,
        },
    ]


def test_manifest_pins_source_and_output_with_qualification_limits(tmp_path):
    """The same 3-row fixture has 2 known actuals and 1 unknown (3 - 2)."""
    source = write_source(tmp_path, sample())
    files = exporter().build_dataset(tmp_path)
    manifest = json.loads(files["manifest.json"])
    assert manifest["source"] == {
        "path": SOURCE.as_posix(),
        "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "bytes": len(source.read_bytes()),
    }
    assert manifest["configs"]["matched_concepts"]["rows"] == 3
    assert manifest["configs"]["matched_concepts"]["unknown_actual"] == 1
    assert (
        manifest["configs"]["matched_concepts"]["sha256"]
        == hashlib.sha256(files["matched_concepts.jsonl"]).hexdigest()
    )
    assert manifest["qualification"]["status"] == "NOT_EVALUATED"
    assert manifest["data_limits"]
    card = files["README.md"].decode()
    assert "license: cc-by-4.0" in card
    assert "config_name: matched_concepts" in card
    assert "path: matched_concepts.jsonl" in card
    assert "split: train" in card
    assert "NOT_EVALUATED" in card


def test_invalid_match_does_not_become_a_dataset(tmp_path):
    """An unknown actual cannot be scored false (PortfolioRow.is_match)."""
    data = sample()
    data["fields"][0]["match"] = False
    write_source(tmp_path, data)
    with pytest.raises(ValueError, match="match"):
        exporter().build_dataset(tmp_path)


@pytest.mark.parametrize(
    "change",
    [
        lambda data: data.update(n_total=4),
        lambda data: data.update(n_with_actual=3),
        lambda data: data.update(n_matched=True),
        lambda data: data.update(top1_match_rate=1.0),
        lambda data: data["fields"][0].update(name=""),
        lambda data: data["fields"][0].update(block=None),
        lambda data: data["fields"][0].update(recommended=[]),
        lambda data: data["fields"][0].update(actual=""),
        lambda data: data["fields"][1].update(match=0),
        lambda data: data["fields"][1].pop("actual"),
        lambda data: data["fields"].append(data["fields"][0].copy()),
        lambda data: data.update(fields={}),
        lambda data: data.update(fields=[]),
    ],
)
def test_invalid_summary_is_rejected(tmp_path, change):
    """Alter one of the independently calculated fixture facts; none is valid."""
    data = sample()
    change(data)
    write_source(tmp_path, data)
    with pytest.raises(ValueError):
        exporter().build_dataset(tmp_path)


@pytest.mark.parametrize(
    "raw",
    [
        '{"fields": [], "n_total": 0, "n_total": 1}',
        '{"fields": [], "top1_match_rate": NaN}',
        '{"fields": [], "top1_match_rate": Infinity}',
        "[]",
    ],
)
def test_ambiguous_json_is_rejected(tmp_path, raw):
    """Duplicate keys and non-finite tokens cannot form an auditable input."""
    path = write_source(tmp_path, sample())
    path.write_text(raw, encoding="utf-8")
    with pytest.raises(ValueError):
        exporter().build_dataset(tmp_path)


def test_all_unknown_actuals_remain_unscored(tmp_path):
    """Hand calculation: one unknown row gives no scored rows, not a failure.

    The source summarize convention records 0.0 for a zero denominator;
    exporting that source convention must not convert null match into false.
    """
    data = sample()
    data.update(
        fields=data["fields"][:1],
        n_total=1,
        n_with_actual=0,
        n_matched=0,
        top1_match_rate=0.0,
    )
    write_source(tmp_path, data)
    files = exporter().build_dataset(tmp_path)
    rows = [json.loads(line) for line in files["matched_concepts.jsonl"].splitlines()]
    assert rows[0]["match"] is None
    assert (
        json.loads(files["manifest.json"])["configs"]["matched_concepts"][
            "unknown_actual"
        ]
        == 1
    )


def test_output_bytes_are_reproducible_with_shuffled_rows(tmp_path):
    """Sorting changes order only; source byte digests still record that change."""
    data = sample()
    write_source(tmp_path, data)
    module = exporter()
    first = module.build_dataset(tmp_path)
    assert module.build_dataset(tmp_path) == first
    data["fields"].reverse()
    write_source(tmp_path, data)
    second = module.build_dataset(tmp_path)
    assert first["matched_concepts.jsonl"] == second["matched_concepts.jsonl"]
    assert first["README.md"] == second["README.md"]
    assert (
        json.loads(first["manifest.json"])["source"]["sha256"]
        != json.loads(second["manifest.json"])["source"]["sha256"]
    )


def test_cli_writes_a_readable_resumable_bundle(tmp_path, capsys):
    """An identical second invocation preserves every generated byte."""
    root = tmp_path / "source"
    source = write_source(root, sample())
    before = source.read_bytes()
    out = tmp_path / "candidate"
    module = exporter()
    args = ["--repo-root", str(root), "--output", str(out)]
    assert module.main(args) == 0
    first = {path.name: path.read_bytes() for path in out.iterdir()}
    assert set(first) == {"README.md", "manifest.json", "matched_concepts.jsonl"}
    assert module.main(args) == 0
    assert first == {path.name: path.read_bytes() for path in out.iterdir()}
    assert source.read_bytes() == before
    assert "matched_concepts: 3 rows" in capsys.readouterr().out


@pytest.mark.parametrize("destination", ["same", "child", "parent"])
def test_cli_rejects_output_overlapping_source(tmp_path, destination):
    """Every overlap is rejected before the source or output can be changed."""
    root = tmp_path / "source"
    source = write_source(root, sample())
    before = source.read_bytes()
    out = {"same": root, "child": root / "candidate", "parent": tmp_path}[destination]
    with pytest.raises(ValueError, match="overlap"):
        exporter().main(["--repo-root", str(root), "--output", str(out)])
    assert source.read_bytes() == before
    assert not (out / "manifest.json").exists()


def test_cli_preserves_changed_existing_output(tmp_path):
    """No output is written when even one candidate file has different bytes."""
    root = tmp_path / "source"
    write_source(root, sample())
    out = tmp_path / "candidate"
    out.mkdir()
    (out / "README.md").write_bytes(b"preserved")
    with pytest.raises(ValueError, match="existing"):
        exporter().main(["--repo-root", str(root), "--output", str(out)])
    assert {p.name: p.read_bytes() for p in out.iterdir()} == {
        "README.md": b"preserved"
    }


def test_committed_source_projection_matches_independent_counts():
    """Compute coverage independently from committed rows, without fixed counts."""
    source = json.loads((REPO / SOURCE).read_bytes())
    files = exporter().build_dataset(REPO)
    manifest = json.loads(files["manifest.json"])
    config = manifest["configs"]["matched_concepts"]
    assert config["rows"] == len(source["fields"])
    assert config["unknown_actual"] == len(
        [row for row in source["fields"] if row["actual"] is None]
    )
    assert len(files["matched_concepts.jsonl"].splitlines()) == len(source["fields"])


def test_cli_invalid_source_creates_no_output(tmp_path):
    """Failing validation cannot leave an apparently usable partial dataset."""
    root = tmp_path / "source"
    data = sample()
    data["n_total"] = 4  # Fixture has only three rows, as enumerated in sample().
    source = write_source(root, data)
    before = source.read_bytes()
    out = tmp_path / "candidate"
    with pytest.raises(ValueError):
        exporter().main(["--repo-root", str(root), "--output", str(out)])
    assert not out.exists()
    assert source.read_bytes() == before


def test_cli_rejects_symlink_output_alias_to_source(tmp_path):
    """Resolving an alias must preserve the same source/output boundary."""
    root = tmp_path / "source"
    source = write_source(root, sample())
    alias = tmp_path / "alias"
    alias.symlink_to(root, target_is_directory=True)
    before = source.read_bytes()
    with pytest.raises(ValueError, match="overlap"):
        exporter().main(["--repo-root", str(root), "--output", str(alias)])
    assert source.read_bytes() == before


def test_cli_rejects_linked_candidate_file_without_altering_target(tmp_path):
    """Even matching bytes cannot authorize modification through a file link."""
    root = tmp_path / "source"
    write_source(root, sample())
    module = exporter()
    card = module.build_dataset(root)["README.md"]
    target = tmp_path / "retained-card"
    target.write_bytes(card)
    out = tmp_path / "candidate"
    out.mkdir()
    (out / "README.md").symlink_to(target)
    with pytest.raises(ValueError, match="existing"):
        module.main(["--repo-root", str(root), "--output", str(out)])
    assert target.read_bytes() == card
    assert not (out / "matched_concepts.jsonl").exists()


def test_cli_resumes_an_identical_partial_bundle(tmp_path):
    """A retained correct table is sufficient to resume the missing metadata."""
    root = tmp_path / "source"
    write_source(root, sample())
    module = exporter()
    expected = module.build_dataset(root)
    out = tmp_path / "candidate"
    out.mkdir()
    (out / "matched_concepts.jsonl").write_bytes(expected["matched_concepts.jsonl"])
    assert module.main(["--repo-root", str(root), "--output", str(out)]) == 0
    assert {p.name: p.read_bytes() for p in out.iterdir()} == expected
