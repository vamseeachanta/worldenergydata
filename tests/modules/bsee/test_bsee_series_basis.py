"""Pinned BSEE well snapshot used as the article series' single source of truth (23 Nov 2026).

The snapshot cannot be re-downloaded (BSEE rebuilds the files daily at the same URL), so its manifest
is the only durable record of which bytes every published well count came from.
"""

import json
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "data/modules/bsee/series_basis/2026-11-23/manifest.json"
REGISTRY = ROOT / "data/catalog/source-registry.yml"
EXPECTED = {"BoreholeRawData", "eWellEORRawData", "eWellAPMRawData", "eWellWARRawData"}
SNAPSHOT_DATE = "2026-11-23"
MAX_SITTING = timedelta(minutes=30)
HEX64 = re.compile(r"[0-9a-f]{64}")
UTC_STAMP = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

# Generic forms of a machine-local location; a public manifest names none of them.
LOCAL_LOCATION = [
    r"/mnt/",
    r"/home/",
    r"/Users/",
    r"/Volumes/",
    r"\b[A-Za-z]:[\\/]",
    r"\\\\[A-Za-z0-9]",
    r"\bfile://",
    r"\bssh://",
    r"\b[\w.-]+@[\w-]+",
    r"(?<!\w)~/",
    r"\b10\.\d+\.\d+\.\d+\b",
    r"\b192\.168\.\d+\.\d+\b",
    r"\b172\.(1[6-9]|2\d|3[01])\.\d+\.\d+\b",
    r"\b100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d+\.\d+\b",
    r"\.ts\.net\b",
    r"\.local\b",
]


def _json_no_duplicates(pairs):
    keys = [k for k, _ in pairs]
    dup = {k for k in keys if keys.count(k) > 1}
    assert not dup, f"duplicate keys in manifest.json: {sorted(dup)}"
    return dict(pairs)


def _utc(s):
    assert UTC_STAMP.fullmatch(s), f"not an explicit UTC timestamp: {s!r}"
    return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _no_duplicates(loader, node, deep=False):
    keys = [loader.construct_object(k, deep=deep) for k, _ in node.value]
    dup = {k for k in keys if keys.count(k) > 1}
    assert not dup, f"duplicate keys in source-registry.yml: {sorted(dup)}"
    return loader.construct_mapping(node, deep)


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_duplicates
)


@pytest.fixture(scope="module")
def manifest():
    assert MANIFEST.is_file(), f"missing pinned manifest {MANIFEST.relative_to(ROOT)}"
    return json.loads(
        MANIFEST.read_text(encoding="utf-8"), object_pairs_hook=_json_no_duplicates
    )


@pytest.fixture(scope="module")
def bsee_registry():
    reg = yaml.load(REGISTRY.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    return reg["modules"]["bsee"]["datasets"]


def test_manifest_lists_the_four_well_files_once_each(manifest):
    names = [f["name"] for f in manifest["files"]]
    assert len(names) == len(set(names)) == len(EXPECTED)
    assert all(n.endswith(".zip") for n in names)
    assert {n.removesuffix(".zip") for n in names} == EXPECTED


def test_each_file_has_digest_blob_and_bsee_source(manifest):
    for f in manifest["files"]:
        assert HEX64.fullmatch(f["sha256"]), f["name"]
        assert f["blob"] == f"blobs/sha256/{f['sha256'][:2]}/{f['sha256']}.zip"
        assert f["source_url"] == f"https://www.data.bsee.gov/Well/Files/{f['name']}"
        assert f["bytes"] > 0


def test_members_are_unique_and_carry_digests(manifest):
    for f in manifest["files"]:
        names = [m["name"] for m in f["members"]]
        assert len(names) == len(set(names)), f["name"]
        files = [m for m in f["members"] if not m["name"].endswith("/")]
        assert files, f"{f['name']} lists no data member"
        for m in files:
            assert HEX64.fullmatch(m["sha256"]), m["name"]
            assert m["bytes"] > 0, m["name"]
            assert m["zip_date_local"].startswith(SNAPSHOT_DATE + " "), m["name"]


def test_index_page_is_retained_with_its_digest(manifest):
    ip = manifest["index_page"]
    assert HEX64.fullmatch(ip["sha256"])
    assert ip["retained"] is True
    assert ip["blob"] == f"blobs/sha256/{ip['sha256'][:2]}/{ip['sha256']}.html"
    assert ip["bytes"] > 0


def test_downloads_fall_inside_one_short_sitting(manifest):
    start, end = _utc(manifest["sitting_utc_start"]), _utc(manifest["sitting_utc_end"])
    assert timedelta(0) <= end - start <= MAX_SITTING
    assert start <= _utc(manifest["index_page"]["saved_utc"]) <= end
    for f in manifest["files"]:
        assert start <= _utc(f["downloaded_utc"]) <= end, f["name"]


def test_every_file_is_from_the_same_bsee_build_date(manifest):
    for f in manifest["files"]:
        built = parsedate_to_datetime(f["http_last_modified"])
        assert built.tzinfo is not None, f["name"]
        built_date = built.astimezone(timezone.utc).date().isoformat()
        assert built_date == SNAPSHOT_DATE, f["name"]
        assert built <= _utc(f["downloaded_utc"]), f["name"]
        page = datetime.strptime(f["bsee_file_date_page_local"], "%m/%d/%Y %I:%M:%S %p")
        assert page.date().isoformat() == SNAPSHOT_DATE, f["name"]
        assert built.replace(tzinfo=None) - page == timedelta(hours=6), f["name"]


def test_not_redownloadable_requires_verified_second_copy(manifest):
    assert manifest["snapshot_date"] == SNAPSHOT_DATE
    assert manifest["re_downloadable"] is False
    second = manifest["storage"]["second_copy"]
    assert second["status"] == "verified"
    assert second["method"].strip()
    expected = sorted([f["name"] for f in manifest["files"]] + ["index_page"])
    assert sorted(second["covers"]) == expected
    assert _utc(second["verified_utc"]) >= _utc(manifest["sitting_utc_end"])


@pytest.mark.parametrize("path", [MANIFEST, REGISTRY], ids=["manifest", "registry"])
def test_public_files_carry_no_machine_local_location(path):
    text = path.read_text(encoding="utf-8")
    for pat in LOCAL_LOCATION:
        assert not re.search(pat, text, re.IGNORECASE), f"{path.name}: matches {pat}"


def test_source_registry_points_each_dataset_at_the_pinned_manifest(
    manifest, bsee_registry
):
    urls = {f["name"].removesuffix(".zip"): f["source_url"] for f in manifest["files"]}
    rel = MANIFEST.relative_to(ROOT).as_posix()
    for name in EXPECTED:
        assert name in bsee_registry, name
        assert bsee_registry[name]["source_url"] == urls[name]
        assert bsee_registry[name]["update_frequency"] == "daily"
        assert bsee_registry[name]["pinned_snapshot"] == rel
