"""Synthetic transport tests; source admission is outside this contract."""

import copy
import hashlib
import importlib.util
import random
from pathlib import Path, PurePosixPath

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = "browser_shard_transport/1.0.0"


def load_script(name):
    spec = importlib.util.spec_from_file_location(
        name, ROOT / "scripts/hf_export" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def pack():
    return load_script("browser_shards").pack_records


def build(pack, records, **changes):
    options = dict(id_key="id", schema=SCHEMA, max_rows=10, max_bytes=1000)
    options.update(changes)
    return pack("fields", records, **options)


def test_exact_bytes_and_metadata(pack):
    result = build(pack, [{"z": "é", "id": "a"}])
    raw = '[{"id":"a","z":"é"}]\n'.encode("utf-8")
    assert result == {
        "table": "fields",
        "schema": SCHEMA,
        "record_count": 1,
        "byte_count": len(raw),
        "shards": [
            {
                "path": "browser/fields/000000.json",
                "sha256": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "record_count": 1,
                "media_type": "application/json",
                "schema": SCHEMA,
                "data": raw,
            }
        ],
    }


def test_permutations_conserve_101_records_without_mutating_inputs(pack):
    records = [{"value": [i, None, True], "id": f"r{i:03}"} for i in range(101)]
    original = copy.deepcopy(records)
    expected_ids = [f"r{i:03}" for i in range(101)]
    result = build(pack, records, max_rows=7, max_bytes=240)
    parser = load_script("explorer_visualization").strict_json
    seen = []
    for i, shard in enumerate(result["shards"]):
        raw = shard["data"]
        rows = parser(raw)
        assert 0 < len(rows) <= 7
        assert len(raw) <= 240
        assert shard["record_count"] == len(rows)
        assert shard["byte_count"] == len(raw)
        assert shard["sha256"] == hashlib.sha256(raw).hexdigest()
        assert shard["path"] == f"browser/fields/{i:06}.json"
        assert not PurePosixPath(shard["path"]).is_absolute()
        assert ".." not in PurePosixPath(shard["path"]).parts
        seen.extend(row["id"] for row in rows)
    assert seen == expected_ids
    assert result["record_count"] == 101
    assert result["byte_count"] == sum(len(s["data"]) for s in result["shards"])
    for seed in range(5):
        shuffled = copy.deepcopy(records)
        random.Random(seed).shuffle(shuffled)
        shuffled = [dict(reversed(list(row.items()))) for row in shuffled]
        assert build(pack, shuffled, max_rows=7, max_bytes=240) == result
    assert records == original


def test_row_and_utf8_byte_boundaries(pack):
    records = [{"id": "a", "v": "é"}, {"id": "b", "v": "é"}]
    raw = '[{"id":"a","v":"é"},{"id":"b","v":"é"}]\n'.encode()
    assert len(build(pack, records, max_bytes=len(raw))["shards"]) == 1
    assert len(build(pack, records, max_bytes=len(raw) - 1)["shards"]) == 2
    assert len(build(pack, records, max_rows=1)["shards"]) == 2
    single_size = len('[{"id":"a","v":"é"}]\n'.encode())
    assert len(build(pack, records[:1], max_bytes=single_size)["shards"]) == 1
    with pytest.raises(ValueError, match="byte bound"):
        build(pack, records, max_bytes=single_size - 1)


@pytest.mark.parametrize(
    "table", ["fields", "wells", "countries", "parametric_economics"]
)
def test_empty_table_and_explicit_id_key(pack, table):
    empty = pack(table, [], id_key="key", schema=SCHEMA, max_rows=1, max_bytes=1)
    assert empty == dict(
        table=table, schema=SCHEMA, record_count=0, byte_count=0, shards=[]
    )
    result = pack(
        table, [{"key": "a"}], id_key="key", schema=SCHEMA, max_rows=1, max_bytes=100
    )
    assert result["shards"][0]["path"] == f"browser/{table}/000000.json"


@pytest.mark.parametrize("key", ["max_rows", "max_bytes"])
@pytest.mark.parametrize("value", [0, -1, True, False, 1.5, "2", None])
def test_invalid_bounds(pack, key, value):
    with pytest.raises(ValueError):
        build(pack, [], **{key: value})


@pytest.mark.parametrize(
    "records",
    [
        [{"id": "a"}, {"id": "a"}],
        [{"id": ""}],
        [{"id": "  "}],
        [{}],
        [{"id": 1}],
        [None],
        [["a"]],
        [{"id": "a", "v": {1: "bad"}}],
        [{"id": "a", "v": (1, 2)}],
        [{"id": "a", "v": {"nested": [float("nan")]}}],
        [{"id": "a", "v": float("inf")}],
        [{"id": "a", "v": float("-inf")}],
        [{"id": "a", "v": ["<script>alert(1)</script>"]}],
        [{"id": "a", "<b>": "value"}],
        [{"id": "<b>a</b>"}],
    ],
)
def test_invalid_records_fail_instead_of_dropping_or_sanitizing(pack, records):
    with pytest.raises(ValueError):
        build(pack, records)


@pytest.mark.parametrize(
    "changes",
    [
        {"schema": "unknown/1"},
        {"schema": None},
        {"id_key": ""},
        {"id_key": " "},
        {"id_key": 1},
    ],
)
def test_invalid_schema_or_id_key(pack, changes):
    with pytest.raises(ValueError):
        build(pack, [], **changes)


@pytest.mark.parametrize(
    "table", ["../fields", "/fields", "fields/extra", "unknown", None]
)
def test_table_names_cannot_supply_paths(pack, table):
    with pytest.raises(ValueError):
        pack(table, [], id_key="id", schema=SCHEMA, max_rows=1, max_bytes=100)
