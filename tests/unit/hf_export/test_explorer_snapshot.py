"""Snapshot contract tests using independent counts and strict JSON byte examples.

The synthetic example has two fields, one well, one country and one surfaced
scenario: counts are obtained by enumeration here, without financial computation.
Shard examples partition five rows into pairs: [2, 2, 1]. These are test inputs,
not empirical coefficients or acceptance limits (issue #1045 contract).
"""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location(
    "explorer_snapshot", REPO / "scripts/hf_export/explorer_snapshot.py"
)
snapshot = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshot)


def raw(value):
    return json.dumps(value, ensure_ascii=False).encode()


@pytest.fixture
def case():
    sources = {
        "explorer.json": raw(
            {
                "fields": {
                    "alpha": {
                        "id": "alpha",
                        "name": "Alpha",
                        "provenance": "Public data",
                        "metrics": [],
                        "architecture": {"svg": "<svg/>"},
                    },
                    "beta": {"id": "beta", "name": "Beta", "provenance": "Public data"},
                },
                "wells": {
                    "wells": [
                        {
                            "api": "123456789012",
                            "field_id": "alpha",
                            "slot": "A",
                            "cum_oil_mmbbl": 2.5,
                        }
                    ]
                },
            }
        ),
        "atlas.json": raw(
            {
                "countries": [{"country": "Example", "fields": 5}],
                "fields": [{"catalog_id": str(i)} for i in range(5)],
            }
        ),
        "performance.json": raw(
            {
                "fields": {
                    "alpha": {
                        "wells": 1,
                        "economics_status": "surfaced",
                        "npv_mm": 2.5,
                    },
                    "beta": {
                        "wells": 0,
                        "economics_status": "early_life",
                        "npv_mm": None,
                    },
                }
            }
        ),
        "parametric.json": raw(
            {
                "fields": {
                    "alpha": {
                        "economics_status": "surfaced",
                        "grid": [
                            {
                                "wti_price_multiplier": 1.0,
                                "discount_rate": 0.1,
                                "npv_musd": 2.5,
                            }
                        ],
                        "breakeven_multiplier_by_rate": {"0.1": 0.9},
                    }
                }
            }
        ),
        "registry.json": raw(
            {
                "fields": [
                    {
                        "canonical_id": "alpha",
                        "display_name": "Alpha",
                        "fdp_slug": "alpha",
                        "aliases": ["First"],
                    },
                    {
                        "canonical_id": "beta",
                        "display_name": "Beta",
                        "fdp_slug": "beta",
                        "aliases": [],
                    },
                ]
            }
        ),
    }
    config = {
        "schema_version": "1.0.0",
        "dataset_id": "namespace/dataset",
        "source_repository": "https://example.org/energy.git",
        "source_git_sha": "a" * 40,
        "generator_version": "1.0.0",
        "license": "cc-by-4.0",
        "shard_max_records": 2,
        "shard_max_bytes": 20000,
        "inputs": {},
    }
    for role, path in zip(
        ("explorer", "atlas", "performance", "parametric", "registry"), sources
    ):
        config["inputs"][role] = {
            "path": path,
            "sha256": hashlib.sha256(sources[path]).hexdigest(),
            "classification": "public",
            "license": "cc-by-4.0",
            "redistribution": "confirmed",
            "evidence": "https://example.org/license",
        }
    return config, sources


def build(case):
    config, sources = case
    return snapshot.build_snapshot(config, sources.__getitem__, "namespace/dataset")


def change_source(case, role, edit):
    config, sources = case
    entry = config["inputs"][role]
    value = json.loads(sources[entry["path"]])
    edit(value)
    sources[entry["path"]] = raw(value)
    entry["sha256"] = hashlib.sha256(sources[entry["path"]]).hexdigest()


def records(files, collection):
    manifest = json.loads(files["browser/manifest.json"])
    return [
        row
        for entry in manifest["artifacts"]
        if entry.get("collection") == collection and entry["kind"] == "browser"
        for row in json.loads(files[entry["path"]])
    ]


def test_repeatable_complete_snapshot(case):
    files = build(case)
    assert files == build(
        (copy.deepcopy(case[0]), dict(reversed(list(case[1].items()))))
    )
    m = json.loads(files["browser/manifest.json"])
    assert m["counts"] == {
        "fields": 2,
        "wells": 1,
        "countries": 1,
        "parametric_economics": 1,
        "catalog_fields": 5,
    }
    assert "hf_commit_sha" not in m
    assert {f"{name}.json" for name in snapshot.COLLECTIONS} <= files.keys()
    assert records(files, "fields")[1]["readiness"] == "zero_well_ready"
    well = records(files, "wells")[0]
    assert well["well_id"] == "bsee-api12:123456789012"
    assert well["parent_field_id"] == "alpha"
    assert records(files, "fields")[0]["aliases"] == ["First"]
    assert "svg" not in json.dumps(records(files, "fields"))
    snapshot.validate_snapshot(files)


def test_canonical_json_bytes():
    """Hand serialization: lexical keys, compact separators, UTF-8, one LF."""
    assert snapshot.canonical_json({"z": 2, "a": "é"}) == b'{"a":"\xc3\xa9","z":2}\n'


@pytest.mark.parametrize(
    "key,value",
    [
        ("schema_version", "9.0.0"),
        ("dataset_id", "namespace/other"),
        ("source_git_sha", "main"),
        ("source_git_sha", "0" * 40),
        ("shard_max_records", 0),
        ("shard_max_records", True),
        ("shard_max_bytes", 1),
        ("license", "other"),
    ],
)
def test_invalid_configuration(case, key, value):
    case[0][key] = value
    with pytest.raises(ValueError):
        build(case)


@pytest.mark.parametrize(
    "key,value",
    [
        ("path", "../bad.json"),
        ("path", "/absolute.json"),
        ("path", "bad%2fpath.json"),
        ("path", "bad\\path.json"),
        ("sha256", "b" * 64),
        ("redistribution", "pending"),
        ("license", "other"),
        ("license", "cc0-1.0"),
        ("classification", "private"),
        ("evidence", ""),
    ],
)
def test_invalid_source_admission(case, key, value):
    case[0]["inputs"]["explorer"][key] = value
    with pytest.raises(ValueError):
        build(case)


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
        "<script>alert(1)</script>",
        "&lt;svg&gt;",
        "javascript:alert(1)",
    ],
)
def test_unsafe_projected_values(case, value):
    change_source(
        case, "performance", lambda d: d["fields"]["alpha"].update(npv_mm=value)
    )
    with pytest.raises(ValueError):
        build(case)


def test_duplicate_json_keys(case):
    path = case[0]["inputs"]["explorer"]["path"]
    case[1][path] = b'{"fields":{},"fields":{}}'
    case[0]["inputs"]["explorer"]["sha256"] = hashlib.sha256(case[1][path]).hexdigest()
    with pytest.raises(ValueError):
        build(case)


@pytest.mark.parametrize(
    "role,edit",
    [
        (
            "explorer",
            lambda d: d["wells"]["wells"].append(d["wells"]["wells"][0].copy()),
        ),
        ("explorer", lambda d: d["wells"]["wells"][0].update(field_id="missing")),
        ("explorer", lambda d: d["wells"]["wells"][0].update(api="slot-A")),
        ("explorer", lambda d: d["fields"]["alpha"].update(id="different")),
        ("performance", lambda d: d["fields"]["alpha"].update(wells=2)),
        ("registry", lambda d: d["fields"].append(d["fields"][0].copy())),
        ("registry", lambda d: d["fields"][1].update(aliases=["First"])),
        ("registry", lambda d: d["fields"][1].update(fdp_slug="alpha")),
        ("atlas", lambda d: d["countries"].append(d["countries"][0].copy())),
        (
            "parametric",
            lambda d: d["fields"]["alpha"]["grid"].append(
                d["fields"]["alpha"]["grid"][0].copy()
            ),
        ),
        ("parametric", lambda d: d["fields"].update(missing=d["fields"]["alpha"])),
    ],
)
def test_identity_and_completeness_failures(case, role, edit):
    change_source(case, role, edit)
    with pytest.raises(ValueError):
        build(case)


def test_deterministic_shards_beyond_legacy_cap(case):
    """101 numbered rows, bound 2: 50 pairs plus one, totals 101 exactly."""
    change_source(
        case,
        "atlas",
        lambda d: d.update(
            countries=[{"country": f"country-{i:03}", "fields": 1} for i in range(101)]
        ),
    )
    files = build(case)
    rows = records(files, "countries")
    assert len(rows) == 101
    assert len({r["country"] for r in rows}) == 101
    m = json.loads(files["browser/manifest.json"])
    sizes = [
        a["record_count"]
        for a in m["artifacts"]
        if a["collection"] == "countries" and a["kind"] == "browser"
    ]
    assert sizes == [2] * 50 + [1]


@pytest.mark.parametrize(
    "max_bytes,shard_sizes", [(57, [2]), (56, [1, 1]), (30, [1, 1])]
)
def test_byte_bounded_sharding(max_bytes, shard_sizes):
    """Literal rows occupy 26/27 bytes; brackets and LF add 3, comma adds 1."""
    pair = b'[{"country":"A","fields":1},{"country":"\xc3\xa9","fields":1}]\n'
    first = b'[{"country":"A","fields":1}]\n'
    second = b'[{"country":"\xc3\xa9","fields":1}]\n'
    assert len(pair) == 57
    assert len(first) == 29
    assert len(second) == 30
    shards = list(snapshot._shards(json.loads(pair), 2, max_bytes))
    assert [len(shard) for shard in shards] == shard_sizes
    assert [snapshot.canonical_json(shard) for shard in shards] == (
        [pair] if max_bytes == 57 else [first, second]
    )


def test_single_utf8_record_one_byte_over_bound():
    # The 27-byte object plus two brackets and LF requires exactly 30 bytes.
    record = b'[{"country":"\xc3\xa9","fields":1}]\n'
    with pytest.raises(ValueError, match="single record exceeds byte bound"):
        list(snapshot._shards(json.loads(record), 2, 29))


def test_empty_shard_byte_bound():
    assert [snapshot.canonical_json(part) for part in snapshot._shards([], 2, 3)] == [
        b"[]\n"
    ]
    with pytest.raises(ValueError, match="empty shard exceeds byte bound"):
        list(snapshot._shards([], 2, 2))


@pytest.mark.parametrize("mutation", ["bytes", "count", "schema", "missing", "extra"])
def test_staged_tampering_rejected(case, mutation):
    files = build(case)
    m = json.loads(files["browser/manifest.json"])
    entry = m["artifacts"][0]
    if mutation == "bytes":
        files[entry["path"]] += b" "
    elif mutation == "count":
        entry["record_count"] += 1
        files["browser/manifest.json"] = snapshot.canonical_json(m)
    elif mutation == "schema":
        m["schema_version"] = "2.0.0"
        files["browser/manifest.json"] = snapshot.canonical_json(m)
    elif mutation == "missing":
        del files[entry["path"]]
    else:
        files["unexpected.json"] = b"[]\n"
    with pytest.raises(ValueError):
        snapshot.validate_snapshot(files)


class Backend:
    def __init__(self, files, fail=None):
        self.files = files
        self.calls = []
        self.fail = fail

    def commit(self, dataset_id, parent, files):
        self.calls.append(("commit", dataset_id, parent, set(files)))
        if self.fail == "race":
            raise RuntimeError("race")
        return "b" * 40

    def read(self, dataset_id, sha, path):
        self.calls.append(("read", dataset_id, sha, path))
        if self.fail == "read":
            raise RuntimeError("read failure")
        return self.files[path] + (b" " if self.fail == "corrupt" else b"")


def test_publish_one_commit_and_all_exact_reads(case):
    files = build(case)
    backend = Backend(files)
    receipt = snapshot.publish_snapshot(files, "c" * 40, backend)
    assert backend.calls[0] == ("commit", "namespace/dataset", "c" * 40, set(files))
    assert len(backend.calls) == 1 + len(files)
    assert all(c[2] == "b" * 40 for c in backend.calls[1:])
    assert receipt["hf_commit_sha"] == "b" * 40
    assert receipt["source_git_sha"] == "a" * 40
    assert receipt["compatibility"]["status"] == "versioned_migration_required"
    assert set(receipt["hashes"]) == set(files)


@pytest.mark.parametrize("failure", ["race", "read", "corrupt"])
def test_publication_failure_has_no_receipt(case, failure):
    files = build(case)
    with pytest.raises((ValueError, RuntimeError)):
        snapshot.publish_snapshot(files, "c" * 40, Backend(files, failure))


def test_dry_run_never_touches_backend(case):
    summary = snapshot.publish_snapshot(build(case), None, None, dry_run=True)
    assert summary["publication"] == "not_published"
    assert "hf_commit_sha" not in summary


def test_invalid_parent_never_uploads(case):
    files = build(case)
    backend = Backend(files)
    with pytest.raises(ValueError):
        snapshot.publish_snapshot(files, "main", backend)
    assert not backend.calls


@pytest.mark.parametrize("status", ["early_life", "unlisted", "not_evaluated"])
def test_publish_rejects_scenario_with_withheld_parent(case, status):
    files = build(case)
    manifest = json.loads(files["browser/manifest.json"])
    for entry in manifest["artifacts"]:
        if entry["collection"] == "fields":
            rows = json.loads(files[entry["path"]])
            for row in rows:
                if row["field_id"] == "alpha":
                    row.update(
                        economics_status=status,
                        npv_mm=None,
                        breakeven_wti=None,
                        sens_mm_per_dollar=None,
                    )
            data = snapshot.canonical_json(rows)
            files[entry["path"]] = data
            entry.update(sha256=hashlib.sha256(data).hexdigest(), byte_count=len(data))
    files["browser/manifest.json"] = snapshot.canonical_json(manifest)
    backend = Backend(files)
    with pytest.raises(ValueError, match="conflicting economics admission"):
        snapshot.publish_snapshot(files, "c" * 40, backend)
    assert not backend.calls


def test_publish_rejects_missing_empty_browser_shard(case):
    change_source(case, "parametric", lambda d: d.update(fields={}))
    files = build(case)
    manifest = json.loads(files["browser/manifest.json"])
    empty = [
        entry
        for entry in manifest["artifacts"]
        if entry["collection"] == "parametric_economics" and entry["kind"] == "browser"
    ]
    assert len(empty) == 1
    assert files.pop(empty[0]["path"]) == b"[]\n"
    manifest["artifacts"].remove(empty[0])
    files["browser/manifest.json"] = snapshot.canonical_json(manifest)
    backend = Backend(files)
    with pytest.raises(ValueError, match="incomplete artifact inventory"):
        snapshot.publish_snapshot(files, "c" * 40, backend)
    assert not backend.calls


def test_git_loader_reads_exact_objects_and_refuses_dirty(case, monkeypatch):
    config, sources = case
    config_bytes = raw(config)
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        if args[-1] == "--untracked-files=all":
            return SimpleNamespace(stdout=b"")
        if "rev-parse" in args:
            return SimpleNamespace(stdout=("a" * 40 + "\n").encode())
        spec = args[-1]
        assert spec.startswith("a" * 40 + ":")
        path = spec.split(":", 1)[1]
        return SimpleNamespace(
            stdout=config_bytes if path == "admission.json" else sources[path]
        )

    monkeypatch.setattr(snapshot.subprocess, "run", run)
    assert snapshot.build_from_git(
        REPO, "admission.json", "a" * 40, "namespace/dataset"
    ) == build(case)
    monkeypatch.setattr(
        snapshot.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(stdout=b" M tracked.py\n"),
    )
    with pytest.raises(ValueError, match="clean"):
        snapshot.build_from_git(REPO, "admission.json", "a" * 40, "namespace/dataset")


def test_committed_inventory_normalization():
    """Issue #1045 inventory: enumerate 10 rich fields, 56 API wells, 3 zeroes.

    This is an inventory test, not a redistribution admission or financial check.
    Expected counts are the independently recorded issue inventory; source data
    are read directly, so the stale historical bundle cannot affect the result.
    """
    import yaml

    base = REPO / "reports/lower_tertiary"
    inputs = {
        "explorer": json.loads((base / "lifecycle/_explorer.json").read_bytes()),
        "performance": json.loads((base / "lifecycle/_performance.json").read_bytes()),
        "parametric": json.loads(
            (base / "parametric/lt_economics_parametric.json").read_bytes()
        ),
        "atlas": json.loads(
            (REPO / "reports/field-atlas/_atlas_feed.json").read_bytes()
        ),
        "registry": yaml.safe_load((REPO / "config/fields.yml").read_bytes()),
    }
    tables = snapshot._tables(inputs)
    assert len(tables["fields"]) == 10
    assert len(tables["wells"]) == 56
    assert sum(r["well_count"] == 0 for r in tables["fields"]) == 3


def test_no_source_sha_hash_cycle(case, monkeypatch):
    config, sources = case
    del config["source_git_sha"]

    def run(args, **kwargs):
        if "status" in args:
            return SimpleNamespace(stdout=b"")
        if "rev-parse" in args:
            return SimpleNamespace(stdout=("a" * 40).encode())
        path = args[-1].split(":", 1)[1]
        return SimpleNamespace(
            stdout=raw(config) if path == "admission.json" else sources[path]
        )

    monkeypatch.setattr(snapshot.subprocess, "run", run)
    files = snapshot.build_from_git(
        REPO, "admission.json", "a" * 40, "namespace/dataset"
    )
    assert json.loads(files["browser/manifest.json"])["source_git_sha"] == "a" * 40


def test_missing_performance_needs_explicit_zero(case):
    change_source(case, "performance", lambda d: d["fields"].pop("beta"))
    with pytest.raises(ValueError):
        build(case)
    change_source(case, "explorer", lambda d: d["fields"]["beta"].update(wellsCount=0))
    rows = records(build(case), "fields")
    assert rows[1]["readiness"] == "zero_well_ready"
    assert rows[1]["economics_status"] == "not_evaluated"


@pytest.mark.parametrize("value", [None, "1", True])
def test_scenario_numeric_schema(case, value):
    change_source(
        case,
        "parametric",
        lambda d: d["fields"]["alpha"]["grid"][0].update(npv_musd=value),
    )
    with pytest.raises(ValueError):
        build(case)


def test_unknown_manifest_member_rejected(case):
    files = build(case)
    manifest = json.loads(files["browser/manifest.json"])
    manifest["surprise"] = "unsupported"
    files["browser/manifest.json"] = snapshot.canonical_json(manifest)
    with pytest.raises(ValueError):
        snapshot.validate_snapshot(files)


def test_record_column_schema_is_closed(case):
    files = build(case)
    manifest = json.loads(files["browser/manifest.json"])
    for entry in manifest["artifacts"]:
        if entry["collection"] == "fields":
            rows = json.loads(files[entry["path"]])
            for row in rows:
                row["surprise"] = "unsupported"
            data = snapshot.canonical_json(rows)
            files[entry["path"]] = data
            entry.update(sha256=hashlib.sha256(data).hexdigest(), byte_count=len(data))
            entry["schema"]["columns"].append("surprise")
    files["browser/manifest.json"] = snapshot.canonical_json(manifest)
    with pytest.raises(ValueError):
        snapshot.validate_snapshot(files)


def test_primary_key_type_and_route_golden():
    """RFC 4648 section 10 test vectors: 'f' -> 'CO', unpadded/lowercase."""
    assert snapshot.route_key("f") == "r1-co"
    with pytest.raises(ValueError):
        snapshot.route_key("e\u0301")


def test_invalid_hf_returned_sha(case):
    files = build(case)
    backend = Backend(files)
    backend.commit = lambda *a: "main"
    with pytest.raises(ValueError):
        snapshot.publish_snapshot(files, "c" * 40, backend)
    assert not backend.calls


def test_worked_example_answer():
    spec = importlib.util.spec_from_file_location(
        "snapshot_example", REPO / "examples/hf_export/snapshot_example.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = module.example()
    summary = snapshot.publish_snapshot(files, None, None, dry_run=True)
    assert summary["counts"] == {
        "fields": 2,
        "wells": 1,
        "countries": 1,
        "catalog_fields": 2,
        "parametric_economics": 0,
    }
    assert files == module.example()


def test_repository_template_is_deliberately_not_admitted():
    template = json.loads(
        (REPO / "config/hf_export/explorer_snapshot.example.json").read_bytes()
    )
    template["source_git_sha"] = "a" * 40
    with pytest.raises(ValueError, match="license"):
        snapshot.build_snapshot(
            template, lambda p: (REPO / p).read_bytes(), "namespace/dataset"
        )


@pytest.mark.parametrize("value", [None, "Pending", "", "license: pending"])
def test_license_requires_explicit_identifier(case, value):
    case[0]["license"] = value
    with pytest.raises(ValueError):
        build(case)


def test_withheld_extra_economics_never_leaks(case):
    change_source(
        case,
        "parametric",
        lambda d: d["fields"].update(
            extra={"economics_status": "unlisted", "grid": [{"npv_musd": "withheld"}]}
        ),
    )
    files = build(case)
    assert len(records(files, "parametric_economics")) == 1
    assert "withheld" not in files["parametric_economics.json"].decode()


def test_hash_mismatch_fails_before_publication(case):
    case[0]["inputs"]["atlas"]["sha256"] = "b" * 64
    with pytest.raises(ValueError, match="stale"):
        build(case)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda m: m["sources"]["explorer"].update(redistribution="pending"),
        lambda m: m["generator"].update(version="unknown"),
        lambda m: m["sharding"].update(max_records=0),
        lambda m: m.update(route_key_encoding="unknown"),
        lambda m: m["counts"].update(catalog_fields=-1),
    ],
)
def test_publish_revalidates_admission(case, mutate):
    files = build(case)
    manifest = json.loads(files["browser/manifest.json"])
    mutate(manifest)
    files["browser/manifest.json"] = snapshot.canonical_json(manifest)
    backend = Backend(files)
    with pytest.raises(ValueError):
        snapshot.publish_snapshot(files, "c" * 40, backend)
    assert not backend.calls


def test_analytical_format_migration_is_explicitly_versioned(case):
    manifest = json.loads(build(case)["browser/manifest.json"])
    assert manifest["compatibility"]["analytical_schema_version"] == "2.0.0"


@pytest.mark.parametrize(
    "role,edit",
    [
        ("performance", lambda d: d["fields"]["alpha"].update(npv_mm="not-a-number")),
        ("performance", lambda d: d["fields"]["beta"].update(npv_mm=2.5)),
        (
            "explorer",
            lambda d: d["wells"]["wells"][0].update(cum_oil_mmbbl="not-a-number"),
        ),
    ],
)
def test_typed_measurements_and_withholding(case, role, edit):
    change_source(case, role, edit)
    with pytest.raises(ValueError):
        build(case)
