"""Tests for scripts/generate_catalog.py — per-module schema generation.

Validates:
  1. The script runs without error.
  2. data/catalog.yaml is valid YAML with required top-level fields.
  3. Each per-module schema.yaml has required fields (module, datasets).
  4. Column schemas include name and type for every column.
  5. Idempotency — running twice produces consistent structure.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

# Resolve project root relative to this test file
PROJECT_ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = PROJECT_ROOT / "data" / "catalog.yaml"
DATA_MODULES = PROJECT_ROOT / "data" / "modules"
SCRIPT_PATH = PROJECT_ROOT / "scripts" / "generate_catalog.py"


@pytest.fixture(scope="module", autouse=True)
def generate_catalog(tmp_path_factory):
    """Run the catalog generator once before all tests in this module."""
    output_root = tmp_path_factory.mktemp("catalog")
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--project-root",
            str(PROJECT_ROOT),
            "--external-data-root",
            str(PROJECT_ROOT / "data"),
            "--output-root",
            str(output_root),
        ],
        capture_output=True,
        text=True,
        timeout=120,
        env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
    )
    assert (
        result.returncode == 0
    ), f"generate_catalog.py failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    with pytest.MonkeyPatch.context() as patcher:
        patcher.setattr(
            sys.modules[__name__], "CATALOG_PATH", output_root / "data" / "catalog.yaml"
        )
        patcher.setattr(
            sys.modules[__name__], "DATA_MODULES", output_root / "data" / "modules"
        )
        yield


class TestCatalogYaml:
    """Tests for the top-level data/catalog.yaml."""

    def test_catalog_exists(self):
        assert CATALOG_PATH.exists(), f"Expected {CATALOG_PATH} to exist"

    def test_catalog_is_valid_yaml(self):
        with open(CATALOG_PATH) as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "catalog.yaml should parse to a dict"

    def test_catalog_has_required_fields(self):
        with open(CATALOG_PATH) as f:
            data = yaml.safe_load(f)
        for key in (
            "version",
            "generated_at",
            "total_modules",
            "total_datasets",
            "modules",
        ):
            assert key in data, f"Missing required field: {key}"

    def test_catalog_modules_not_empty(self):
        with open(CATALOG_PATH) as f:
            data = yaml.safe_load(f)
        assert len(data["modules"]) > 0, "Catalog should contain at least one module"

    def test_catalog_total_modules_matches(self):
        with open(CATALOG_PATH) as f:
            data = yaml.safe_load(f)
        assert data["total_modules"] == len(data["modules"])

    def test_catalog_total_datasets_consistent(self):
        with open(CATALOG_PATH) as f:
            data = yaml.safe_load(f)
        computed = sum(len(m.get("datasets", [])) for m in data["modules"].values())
        assert data["total_datasets"] == computed


class TestModuleSchemas:
    """Tests for per-module schema.yaml files."""

    def _module_dirs(self) -> list[Path]:
        """Return module directories that have a schema.yaml."""
        dirs = []
        for p in sorted(DATA_MODULES.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                dirs.append(p)
        return dirs

    def test_at_least_five_modules_have_schemas(self):
        schema_files = [
            d / "schema.yaml"
            for d in self._module_dirs()
            if (d / "schema.yaml").exists()
        ]
        assert (
            len(schema_files) >= 5
        ), f"Expected at least 5 module schemas, found {len(schema_files)}"

    def test_each_schema_is_valid_yaml(self):
        for module_dir in self._module_dirs():
            schema_path = module_dir / "schema.yaml"
            if not schema_path.exists():
                continue
            with open(schema_path) as f:
                data = yaml.safe_load(f)
            assert isinstance(data, dict), f"{schema_path} should parse to a dict"

    def test_each_schema_has_required_fields(self):
        for module_dir in self._module_dirs():
            schema_path = module_dir / "schema.yaml"
            if not schema_path.exists():
                continue
            with open(schema_path) as f:
                data = yaml.safe_load(f)
            assert "module" in data, f"{schema_path}: missing 'module' field"
            assert "datasets" in data, f"{schema_path}: missing 'datasets' field"
            assert isinstance(
                data["datasets"], list
            ), f"{schema_path}: 'datasets' should be a list"

    def test_dataset_entries_have_required_fields(self):
        for module_dir in self._module_dirs():
            schema_path = module_dir / "schema.yaml"
            if not schema_path.exists():
                continue
            with open(schema_path) as f:
                data = yaml.safe_load(f)
            for ds in data.get("datasets", []):
                for field in required_dataset_fields(ds):
                    assert field in ds, (
                        f"{schema_path} dataset '{ds.get('name', '?')}': "
                        f"missing '{field}'"
                    )


class TestColumnSchemas:
    """Tests for column-level schema entries."""

    def _all_datasets(self) -> list[tuple[str, dict]]:
        """Collect (module_name, dataset_dict) pairs with columns."""
        pairs = []
        for module_dir in sorted(DATA_MODULES.iterdir()):
            if not module_dir.is_dir() or module_dir.name.startswith("."):
                continue
            schema_path = module_dir / "schema.yaml"
            if not schema_path.exists():
                continue
            with open(schema_path) as f:
                data = yaml.safe_load(f)
            for ds in data.get("datasets", []):
                if ds.get("columns"):
                    pairs.append((module_dir.name, ds))
        return pairs

    def test_columns_have_name_and_type(self):
        for module_name, ds in self._all_datasets():
            for col in ds["columns"]:
                assert (
                    "name" in col
                ), f"{module_name}/{ds['name']}: column missing 'name'"
                assert "type" in col, (
                    f"{module_name}/{ds['name']}/{col.get('name', '?')}: "
                    "column missing 'type'"
                )

    def test_column_types_are_valid(self):
        valid_types = {
            "string",
            "integer",
            "float",
            "datetime",
            "boolean",
            "str",
            "int",
            "list",
            "dict",
            "NoneType",
            "bool",
            "string|null",
        }
        for module_name, ds in self._all_datasets():
            for col in ds["columns"]:
                assert col["type"] in valid_types, (
                    f"{module_name}/{ds['name']}/{col['name']}: "
                    f"unexpected type '{col['type']}'"
                )

    def test_csv_datasets_have_row_count(self):
        for module_name, ds in self._all_datasets():
            if ds.get("format") == "csv" and not is_contract_metadata(ds):
                assert (
                    "row_count" in ds and ds["row_count"] is not None
                ), f"{module_name}/{ds['name']}: CSV dataset missing row_count"


def catalog_generator():
    """Load the same generator used by the catalog fixture."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("catalog_generator", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def required_dataset_fields(dataset):
    """Contract metadata exempts only measured size, after structural validation."""
    fields = {"name", "path", "format", "columns", "size_bytes"}
    if is_contract_metadata(dataset):
        fields.remove("size_bytes")
    return fields


def synthetic_contract():
    return {
        "name": "synthetic.csv",
        "path": "<output-dir>/synthetic.csv",
        "format": "csv",
        "columns": [{"name": "value", "type": "string"}],
        "status": "local_draft_public_export_requires_maintainer_eligibility",
        "contract_only": True,
    }


def synthetic_module(tmp_path, entries):
    module = tmp_path / "data/modules/synthetic"
    module.mkdir(parents=True)
    path = module / "schema.yaml"
    path.write_text(yaml.safe_dump({"module": "synthetic", "datasets": entries}))
    return path


def test_contract_preservation_is_byte_stable(tmp_path):
    generator = catalog_generator()
    path = synthetic_module(tmp_path, [synthetic_contract()])
    generator.generate_catalog(tmp_path)
    first = path.read_bytes()
    generator.generate_catalog(tmp_path)
    assert path.read_bytes() == first
    assert yaml.safe_load(first)["datasets"] == [synthetic_contract()]


@pytest.mark.parametrize("field", ["name", "path", "format", "columns", "status"])
def test_malformed_contract_is_refused(tmp_path, field):
    entry = synthetic_contract()
    entry.pop(field)
    path = synthetic_module(tmp_path, [entry])
    original = path.read_bytes()
    with pytest.raises(ValueError, match="invalid contract-only"):
        catalog_generator().generate_catalog(tmp_path)
    assert path.read_bytes() == original


def test_duplicate_contract_path_is_refused(tmp_path):
    path = synthetic_module(tmp_path, [synthetic_contract(), synthetic_contract()])
    original = path.read_bytes()
    with pytest.raises(ValueError, match="duplicate contract-only path"):
        catalog_generator().generate_catalog(tmp_path)
    assert path.read_bytes() == original


def test_contract_path_colliding_with_scanned_file_is_refused(tmp_path):
    entry = synthetic_contract()
    path = synthetic_module(tmp_path, [entry])
    scanned = {"datasets": [{"path": entry["path"], "size_bytes": 0}]}
    with pytest.raises(ValueError, match="duplicate contract-only path"):
        catalog_generator()._preserve_contract_entries(scanned, path)


@pytest.mark.parametrize("flag", [False, 1, "true", "false", None])
def test_wrongly_flagged_entry_is_not_exempt(flag):
    entry = synthetic_contract()
    entry["contract_only"] = flag
    with pytest.raises(ValueError, match="invalid contract-only"):
        required_dataset_fields(entry)


def test_ordinary_entry_requires_size_and_contract_requires_structure():
    assert required_dataset_fields({"name": "ordinary.csv"}) == {
        "name",
        "path",
        "format",
        "columns",
        "size_bytes",
    }
    assert required_dataset_fields(synthetic_contract()) == {
        "name",
        "path",
        "format",
        "columns",
    }
    broken = synthetic_contract()
    broken["columns"] = []
    with pytest.raises(ValueError, match="invalid contract-only"):
        required_dataset_fields(broken)
    ordinary = synthetic_contract()
    ordinary.update(path="synthetic.csv", size_bytes=0, row_count=0)
    with pytest.raises(ValueError, match="invalid contract-only"):
        required_dataset_fields(ordinary)


def is_contract_metadata(dataset):
    if "contract_only" not in dataset:
        return False
    catalog_generator().validate_contract_entry(dataset)
    return True
