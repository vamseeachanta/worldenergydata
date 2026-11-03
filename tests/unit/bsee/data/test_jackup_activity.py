"""Offline contracts for the public BSEE activity release."""

import hashlib
import io
import json
import zipfile

import pytest


def pipeline():
    from scripts.bsee import build_jackup_activity

    return build_jackup_activity


def response(payload, request):
    stream = io.BytesIO(payload)
    stream.geturl = lambda: request.full_url
    return stream


def test_download_retains_exact_bytes_and_records_provenance(tmp_path, monkeypatch):
    module = pipeline()
    payload = b"public BSEE download\n"
    monkeypatch.setattr(module, "urlopen", lambda req, **kw: response(payload, req))
    manifest = module.download_sources(tmp_path)
    assert len(manifest["sources"]) == len(module.SOURCES)
    for entry in manifest["sources"]:
        assert (tmp_path / entry["archive_path"]).read_bytes() == payload
        assert entry["sha256"] == hashlib.sha256(payload).hexdigest()
        assert entry["size_bytes"] == len(payload)
        assert entry["url"] == module.SOURCES[entry["file"]]
        assert entry["retrieved_at_utc"].endswith("+00:00")
        assert entry["archive_path"] == (
            f"blobs/sha256/{entry['sha256'][:2]}/{entry['sha256']}.zip"
        )
    assert json.loads((tmp_path / "source_manifest.json").read_text()) == manifest
    module.verify_sources(tmp_path, manifest)


def test_download_does_not_overwrite_existing_evidence(tmp_path):
    module = pipeline()
    entry = next(iter(module.SOURCES))
    (tmp_path / entry).write_bytes(b"retained")
    with pytest.raises(FileExistsError):
        module.download_sources(tmp_path)
    assert (tmp_path / entry).read_bytes() == b"retained"


def test_manifest_digest_and_identity_checks_fail_closed(tmp_path, monkeypatch):
    module = pipeline()
    monkeypatch.setattr(module, "urlopen", lambda req, **kw: response(b"original", req))
    manifest = module.download_sources(tmp_path)
    first = manifest["sources"][0]
    (tmp_path / first["archive_path"]).write_bytes(b"tampered")
    with pytest.raises(ValueError, match="digest"):
        module.verify_sources(tmp_path, manifest)
    (tmp_path / first["archive_path"]).write_bytes(b"original")
    module.verify_sources(tmp_path, manifest)
    first["url"] = "https://example.org/changed"
    with pytest.raises(ValueError, match="identity"):
        module.verify_sources(tmp_path, manifest)


def test_partial_manifest_is_rejected(tmp_path):
    with pytest.raises(ValueError, match="source set"):
        pipeline().verify_sources(tmp_path, {"sources": []})


def test_download_readback_must_match_received_bytes(tmp_path, monkeypatch):
    module = pipeline()
    monkeypatch.setattr(module, "urlopen", lambda req, **kw: response(b"received", req))
    monkeypatch.setattr(module, "digest", lambda path: "0" * 64)
    with pytest.raises(ValueError, match="readback"):
        module.download_sources(tmp_path)


def test_manifest_rejects_a_non_digest_blob_locator(tmp_path, monkeypatch):
    module = pipeline()
    monkeypatch.setattr(module, "urlopen", lambda req, **kw: response(b"received", req))
    manifest = module.download_sources(tmp_path)
    manifest["sources"][0]["sha256"] = "../not-a-digest"
    with pytest.raises(ValueError, match="identity"):
        module.verify_sources(tmp_path, manifest)


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://example.org/data.zip",
        "http://www.data.bsee.gov/data.zip",
    ],
)
def test_download_rejects_every_url_outside_the_fixed_bsee_allowlist(tmp_path, url):
    with pytest.raises(ValueError, match="identity"):
        pipeline().download_one(tmp_path, "eWellWARRawData.zip", url)


def test_download_bound_and_redirect_are_rejected(tmp_path, monkeypatch):
    module = pipeline()
    monkeypatch.setattr(module, "MAX_DOWNLOAD_BYTES", 4)
    monkeypatch.setattr(
        module, "urlopen", lambda req, **kw: response(b"oversized", req)
    )
    with pytest.raises(ValueError, match="size bound"):
        module.download_sources(tmp_path / "large")
    monkeypatch.setattr(
        module,
        "urlopen",
        lambda req, **kw: response(
            b"", type("Request", (), {"full_url": "https://example.org/redirect"})()
        ),
    )
    with pytest.raises(ValueError, match="redirect"):
        module.download_sources(tmp_path / "redirect")


def test_archive_reader_validates_schema_without_extracting_paths(tmp_path):
    archive = tmp_path / "public.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("download/main.txt", '"ID","VALUE"\r\n"01","BSEE"\r\n')
        output.writestr("../unrelated.txt", "ignored")
    rows = list(pipeline().read_rows(archive, "download/main.txt", {"ID", "VALUE"}))
    assert rows == [{"ID": "01", "VALUE": "BSEE"}]
    assert not (tmp_path.parent / "unrelated.txt").exists()
    with pytest.raises(ValueError, match="columns"):
        list(pipeline().read_rows(archive, "download/main.txt", {"MISSING"}))


def test_headerless_rig_list_preserves_bsee_names(tmp_path):
    archive = tmp_path / "rigs.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("rigidlistdelimit.txt", '"01","PUBLIC RIG","JACKUP"\r\n')
    rows = list(
        pipeline().read_rows(
            archive,
            "rigidlistdelimit.txt",
            {"RIG_ID", "RIG_NAME", "RIG_TYPE"},
            fieldnames=["RIG_ID", "RIG_NAME", "RIG_TYPE"],
        )
    )
    assert rows == [{"RIG_ID": "01", "RIG_NAME": "PUBLIC RIG", "RIG_TYPE": "JACKUP"}]


def activity(**changes):
    return {
        "SN_WAR": "1",
        "API_WELL_NUMBER": "600000000001",
        "RIG_NAME": "PUBLIC RIG",
        "WATER_DEPTH": "200",
        "WAR_START_DT": "12/31/1997 12:01:00 AM",
        "WAR_END_DT": "1/6/1998 11:59:00 PM",
        "SURF_AREA_CODE": "MC",
        "SURF_BLOCK_NUM": "001",
        "BUS_ASC_NAME": "PUBLIC OPERATOR",
        "CONTACT_NAME": "excluded",
        "PHONE_NUMBER": "excluded",
        **changes,
    }


def borehole(**changes):
    return {
        "API_WELL_NUMBER": "600000000001",
        "REGION_CODE": "G",
        "WELL_SPUD_DATE": "12/1/1997",
        "WATER_DEPTH": "200",
        **changes,
    }


def rig(**changes):
    return {
        "RIG_ID_NUM": "100",
        "RIG_NAME": "PUBLIC RIG",
        "RIG_TYPE_CODE": "JU",
        **changes,
    }


def test_activity_grain_type_filter_region_and_inclusive_years():
    reports = [
        activity(),
        activity(SN_WAR="2", WAR_START_DT="12/31/2025"),
        activity(SN_WAR="3", WAR_START_DT="1/1/2026"),
        activity(SN_WAR="4", WAR_START_DT="12/31/1996"),
        activity(SN_WAR="5", RIG_NAME="PUBLIC SHIP"),
        activity(SN_WAR="6", RIG_NAME="PUBLIC BOAT"),
        activity(SN_WAR="7", API_WELL_NUMBER="500000000001"),
        activity(SN_WAR="8", RIG_NAME="unknown"),
    ]
    rigs = [
        rig(),
        rig(RIG_ID_NUM="101", RIG_NAME="PUBLIC SHIP", RIG_TYPE_CODE="DS"),
        rig(RIG_ID_NUM="102", RIG_NAME="PUBLIC BOAT", RIG_TYPE_CODE="LB"),
    ]
    rows, counts = pipeline().derive_table(
        reports,
        [borehole(), borehole(API_WELL_NUMBER="500000000001", REGION_CODE="A")],
        rigs,
        [],
        [],
    )
    assert [r["activity_id"] for r in rows] == ["1", "2", "6"]
    assert {r["rig_type"] for r in rows} == {"JU", "LB"}
    assert counts["input_records"] == 8
    assert counts["output_records"] == 3
    assert sum(counts["excluded"].values()) + len(rows) == 8
    assert rows[0]["spud_date"] == "1997-12-01"
    assert rows[0]["release_date"] == ""
    assert rows[0]["activity_end_date"] == "1998-01-06"
    assert "CONTACT_NAME" not in rows[0] and "PHONE_NUMBER" not in rows[0]


def test_deep_8831_ft_jackup_is_retained_flagged_and_cross_checked():
    secondary = [
        {
            "SN_APD": "41",
            "RIG_ID_NUM": "100",
            "RIG_NAME": "PUBLIC RIG",
            "RIG_TYPE_CODE": "DRILLSHIP",
        }
    ]
    rows, counts = pipeline().derive_table(
        [activity(WATER_DEPTH="8831")],
        [borehole(WATER_DEPTH="8831")],
        [rig()],
        secondary,
        [],
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["water_depth_ft"] == "8831"
    assert row["deep_water_flag"] == "true"
    assert row["rig_type_check"] == "conflict"
    assert row["type_check_apd_ids"] == "41"
    assert "depth_above_500_ft" in row["quality_flags"]
    assert counts["deep_water_records"] == 1


@pytest.mark.parametrize(
    "depth,flag",
    [("500", "false"), ("501", "true"), ("", "unknown"), ("-1", "unknown")],
)
def test_depth_boundary_and_missing_values(depth, flag):
    rows, _ = pipeline().derive_table(
        [activity(WATER_DEPTH=depth)],
        [borehole(WATER_DEPTH=depth)],
        [rig()],
        [],
        [],
    )
    assert rows[0]["deep_water_flag"] == flag


def test_borehole_depth_conflict_is_visible_without_replacing_report_depth():
    rows, _ = pipeline().derive_table(
        [activity()], [borehole(WATER_DEPTH="900")], [rig()], [], []
    )
    assert rows[0]["water_depth_ft"] == "200"
    assert rows[0]["borehole_water_depth_ft"] == "900"
    assert rows[0]["deep_water_flag"] == "true"
    assert "water_depth_disagreement" in rows[0]["quality_flags"]


def test_second_record_agreement_and_absence_are_distinct():
    apds = [
        {
            "SN_APD": "42",
            "RIG_ID_NUM": "100",
            "RIG_NAME": "PUBLIC RIG",
            "RIG_TYPE_CODE": "JACKUP",
        }
    ]
    rows, _ = pipeline().derive_table([activity()], [borehole()], [rig()], apds, [])
    assert rows[0]["rig_type_check"] == "agree"
    rows, _ = pipeline().derive_table([activity()], [borehole()], [rig()], [], [])
    assert rows[0]["rig_type_check"] == "unavailable"


def test_duplicates_and_ambiguous_names_cannot_multiply_activity_rows():
    with pytest.raises(ValueError, match="Duplicate activity"):
        pipeline().derive_table([activity(), activity()], [borehole()], [rig()], [], [])
    rigs = [rig(), rig(RIG_ID_NUM="101", RIG_TYPE_CODE="DS")]
    rows, counts = pipeline().derive_table([activity()], [borehole()], rigs, [], [])
    assert rows == []
    assert counts["excluded"]["ambiguous_rig_name"] == 1


def test_bad_dates_do_not_silently_become_in_range_activity():
    rows, counts = pipeline().derive_table(
        [activity(WAR_START_DT="not a date")],
        [borehole()],
        [rig()],
        [],
        [],
    )
    assert rows == []
    assert counts["excluded"]["invalid_activity_start"] == 1


def test_unmatched_8831_ft_source_records_have_an_explicit_disposition():
    rows, counts = pipeline().derive_table(
        [activity(RIG_NAME="UNMATCHED PUBLIC RIG", WATER_DEPTH="8831")],
        [borehole()],
        [rig()],
        [],
        [],
    )
    assert rows == []
    assert counts["source_8831_ft_record_audit"] == [
        {
            "activity_id": "1",
            "api_well_number": "600000000001",
            "rig_name": "UNMATCHED PUBLIC RIG",
            "water_depth_ft": "8831",
            "disposition": "unmatched_rig_name",
        }
    ]


def test_csv_schema_deterministic_compression_and_digest_readback(tmp_path):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    original = {
        "sources": [],
        "owner": "worldenergydata",
        "source_id": "bsee-data-center",
    }
    manifest = module.write_release(first, rows, counts, original, "2026-10-29")
    module.write_release(second, rows, counts, original, "2026-10-29")
    path = first / manifest["table"]["file"]
    assert path.read_bytes() == (second / path.name).read_bytes()
    assert manifest["next_refresh_date"] == "2026-10-30"
    assert manifest["table"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert module.verify_release(first) == rows
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="digest"):
        module.verify_release(first)
