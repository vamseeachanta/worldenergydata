"""Synthetic fixtures for licensed tables that are not distributed."""

import csv
import importlib
import json
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
MODULE_DIR = REPO_ROOT / "data/modules/metocean"
SCHEMA = yaml.safe_load((MODULE_DIR / "schema.yaml").read_text())
# Not distributed: these names identify user-supplied licensed tables.
TABLES = (
    "api_rp2met_hurricane_gom_extremes.csv",  # Not distributed.
    "api_rp2met_us_zone_100yr_waves.csv",  # Not distributed.
    "api_rp2met_gom_extremes_by_region.csv",  # Not distributed.
    "api_rp2met_us_zone_100yr_winds.csv",  # Not distributed.
    "metocean_regional_extremes.csv",  # Not distributed.
    "metocean_hs_tp_occurrence.csv",  # Not distributed.
    "metocean_temperature_ranges.csv",  # Not distributed.
    "marine_growth_terminal_thickness.csv",  # Not distributed.
)


def synthetic_copy(directory, name):
    """Create nonphysical synthetic data with explicit synthetic metadata."""
    entry = next(item for item in SCHEMA["datasets"] if item["name"] == name)
    columns = [column["name"] for column in entry["columns"]]
    row = {
        column["name"]: (
            "SYNTHETIC_NOT_PHYSICAL" if column["type"] == "string" else "-987654321"
        )
        for column in entry["columns"]
    }
    path = directory / ("synthetic_" + name)
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerow(row)
    path.with_suffix(".metadata.json").write_text(
        '{"synthetic": true, "basis": "nonphysical, independently invented"}\n'
    )
    return path, row


@pytest.mark.parametrize("name", TABLES)
def test_supplied_synthetic_copy(tmp_path, name):
    """Every documented schema accepts a supplied synthetic copy."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    path, row = synthetic_copy(tmp_path, name)
    assert licensed_tables.load_licensed_table(name, copy_path=path) == [row]


@pytest.mark.parametrize("name", TABLES)
def test_missing_copy_is_plain(tmp_path, monkeypatch, name):
    """Missing data explains the citation and absence of distributed values."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    monkeypatch.delenv("METOCEAN_LICENSED_DATA_DIR", raising=False)
    with pytest.raises(FileNotFoundError) as error:
        licensed_tables.load_licensed_table(name)
    message = str(error.value)
    assert "API RP 2MET" in message
    assert "Derivation of Metocean Design and Operating Conditions" in message
    assert "edition and table titles: to be completed from the licensed copy" in message
    assert name in message
    assert "licensed" in message
    assert "not distributed with the repository" in message
    with pytest.raises(FileNotFoundError, match="not distributed with the repository"):
        licensed_tables.load_licensed_table(name, copy_path=tmp_path / "missing.csv")


def test_environment_and_argument_precedence(tmp_path, monkeypatch):
    """The argument wins; the environment directory resolves the expected name."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    name = TABLES[0]
    path, row = synthetic_copy(tmp_path, name)
    monkeypatch.setenv("METOCEAN_LICENSED_DATA_DIR", str(tmp_path / "absent"))
    assert licensed_tables.load_licensed_table(name, copy_path=path) == [row]
    (tmp_path / name).write_bytes(path.read_bytes())
    monkeypatch.setenv("METOCEAN_LICENSED_DATA_DIR", str(tmp_path))
    assert licensed_tables.load_licensed_table(name) == [row]


def test_wrong_columns_and_rows(tmp_path):
    """Bad headers and row widths fail without disclosing cell contents."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    name = TABLES[0]
    path, _ = synthetic_copy(tmp_path, name)
    path.write_text("SYNTHETIC_WRONG_COLUMN\nSYNTHETIC_NOT_PHYSICAL\n")
    with pytest.raises(ValueError, match="column names"):
        licensed_tables.load_licensed_table(name, copy_path=path)
    path, _ = synthetic_copy(tmp_path, name)
    with path.open("a") as stream:
        stream.write("SYNTHETIC_SHORT_ROW\n")
    with pytest.raises(ValueError, match="row width"):
        licensed_tables.load_licensed_table(name, copy_path=path)


def test_repository_path_and_symlink_are_refused(tmp_path):
    """Repository-local paths and external symlinks into it are refused."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    local = MODULE_DIR / "schema.yaml"
    with pytest.raises(ValueError, match="outside the repository"):
        licensed_tables.load_licensed_table(TABLES[0], copy_path=local)
    link = tmp_path / "synthetic_link.csv"
    link.symlink_to(local)
    with pytest.raises(ValueError, match="outside the repository"):
        licensed_tables.load_licensed_table(TABLES[0], copy_path=link)


def test_external_cwd_keeps_linked_worktree_boundary(tmp_path, monkeypatch):
    """A linked worktree remains the boundary when cwd is external."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    assert (REPO_ROOT / ".git").exists()
    path, row = synthetic_copy(tmp_path, TABLES[0])
    monkeypatch.chdir(tmp_path)
    assert licensed_tables.load_licensed_table(TABLES[0], copy_path=path) == [row]
    with pytest.raises(ValueError, match="outside the repository"):
        licensed_tables.load_licensed_table(
            TABLES[0], copy_path=MODULE_DIR / "schema.yaml"
        )


def test_unresolved_repository_boundary_is_refused(tmp_path, monkeypatch):
    """Unavailable source-checkout boundaries fail closed."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    monkeypatch.setattr(licensed_tables, "__file__", str(tmp_path / "module.py"))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError, match="Repository boundary cannot be established"):
        licensed_tables.load_licensed_table(TABLES[0], copy_path=tmp_path / "copy.csv")


def test_unknown_table_is_refused(tmp_path):
    """Unrecognized names cannot select arbitrary schema entries."""
    licensed_tables = importlib.import_module(
        "worldenergydata.metocean.licensed_tables"
    )
    with pytest.raises(ValueError, match="Unknown licensed table"):
        licensed_tables.load_licensed_table("synthetic_unknown.csv", copy_path=tmp_path)


def test_tables_are_not_distributed():
    """All licensed entries have external routes and no bundled tables."""
    schema = yaml.safe_load((MODULE_DIR / "schema.yaml").read_text())
    metadata = json.loads((MODULE_DIR / "_metadata.json").read_text())
    assert {
        item["name"] for item in schema["datasets"] if item.get("distributed") is False
    } == set(TABLES)
    for name in TABLES:
        assert not (MODULE_DIR / "curated" / name).exists()
        entry = next(item for item in schema["datasets"] if item["name"] == name)
        assert entry["distributed"] is False
        assert "path" not in entry
        assert "row_count" not in entry
        assert entry["supply"]["environment_variable"] == "METOCEAN_LICENSED_DATA_DIR"
        external = next(
            item for item in metadata["external_datasets"] if item["name"] == name
        )
        assert external["distributed"] is False
        assert "path" not in external
        assert all(item["name"] != name for item in metadata["files"])
    for entry in schema["datasets"]:
        if entry["name"] not in TABLES:
            assert (REPO_ROOT / entry["path"]).exists()
    for catalog in (
        "data/catalog.yaml",
        "data/catalog/data-catalog.yml",
        "data/catalog/source-registry.yml",
    ):
        parsed = yaml.safe_load((REPO_ROOT / catalog).read_text())
        serialized = json.dumps(parsed)
        assert all(name not in serialized for name in TABLES)
        assert "data/modules/metocean/curated" not in serialized


def test_citations_and_provenance():
    """Every external entry cites the same document without weakening provenance."""
    citation = (
        "API RP 2MET, Derivation of Metocean Design and Operating Conditions; "
        "edition and table titles: to be completed from the licensed copy"
    )
    schema = yaml.safe_load((MODULE_DIR / "schema.yaml").read_text())
    metadata = json.loads((MODULE_DIR / "_metadata.json").read_text())
    for entry in schema["datasets"] + metadata["external_datasets"]:
        assert entry["citation"] == citation
    readme = (MODULE_DIR / "README.md").read_text()
    assert citation in readme
    for text in (readme, metadata["provenance"]):
        assert "not established" not in text
        assert "retained legacy" not in text
