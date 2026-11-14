"""Offline contracts for the public BSEE activity release."""

import csv
import gzip
import hashlib
import io
import json
import zipfile
from datetime import date

import pytest

REBUILD_COMMAND = (
    "Rebuild with scripts/bsee/build_jackup_activity.py "
    "--raw-dir RAW --reuse-manifest MANIFEST --output-dir OUTPUT"
)


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
        assert entry["sha256"] == hashlib.sha256(payload).hexdigest(), REBUILD_COMMAND
        assert entry["size_bytes"] == len(payload)
        assert entry["url"] == module.SOURCES[entry["file"]]
        assert entry["retrieved_at_utc"].endswith("+00:00")
        assert entry["archive_path"] == (
            f"blobs/sha256/{entry['sha256'][:2]}/{entry['sha256']}.zip"
        )
    assert (
        json.loads((tmp_path / "source_manifest.json").read_text(encoding="utf-8"))
        == manifest
    )
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
            "rig_reference": "name-sha256:"
            + hashlib.sha256(b"unmatched public rig").hexdigest(),
            "registry_evidence": [],
            "water_depth_ft": "8831",
            "disposition": "unmatched_rig_name",
        }
    ]


@pytest.mark.parametrize("later_date", ["2026-10-30", "2026-11-03"])
def test_csv_schema_deterministic_compression_and_digest_readback(
    tmp_path, monkeypatch, later_date
):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    first, second = tmp_path / "first", tmp_path / "second"
    first.mkdir()
    second.mkdir()
    original = {
        "sources": [],
        "owner": "worldenergydata",
        "source_id": "bsee-data-center",
        "publication_date": "2026-10-29",
    }

    class PublicationDate(date):
        @classmethod
        def today(cls):
            return date.fromisoformat(later_date)

    monkeypatch.setattr(module, "date", PublicationDate)
    manifest = module.write_release(first, rows, counts, original, "2026-10-29")
    PublicationDate.today = classmethod(lambda cls: date(2026, 11, 4))
    module.write_release(second, rows, counts, manifest, "2026-10-29")
    path = first / manifest["table"]["file"]
    for name in (path.name, "manifest.json", "data_card.html"):
        assert (first / name).read_bytes() == (
            second / name
        ).read_bytes(), REBUILD_COMMAND
    assert manifest["publication_date"] == "2026-10-29"
    assert "next_refresh_date" not in manifest
    assert manifest["refresh_basis"]["cadence"] == "manual"
    assert manifest["refresh_basis"]["source_cadence"] == "daily"
    assert (
        manifest["table"]["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    ), REBUILD_COMMAND
    assert module.verify_release(first) == rows
    path.write_bytes(path.read_bytes() + b"tampered")
    with pytest.raises(ValueError, match="digest"):
        module.verify_release(first)


@pytest.mark.parametrize("has_publication_date", [False, True])
def test_refresh_publication_date_is_an_explicit_override(
    tmp_path, has_publication_date
):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    source = {"sources": []}
    if has_publication_date:
        source["publication_date"] = "2026-10-29"
    manifest = module.write_release(
        tmp_path,
        rows,
        counts,
        source,
        "2026-10-29",
        publication_date=date(2026, 11, 4),
    )
    assert manifest["publication_date"] == "2026-11-04"
    assert source == {
        "sources": [],
        **({"publication_date": "2026-10-29"} if has_publication_date else {}),
    }
    assert "2026-11-04" in (tmp_path / "data_card.html").read_text(encoding="utf-8")


@pytest.mark.parametrize("publication_date", ["not-a-date", "", None])
def test_invalid_reused_publication_date_is_rejected_before_writing(
    tmp_path, publication_date
):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    with pytest.raises((ValueError, TypeError)):
        module.write_release(
            tmp_path,
            rows,
            counts,
            {"sources": [], "publication_date": publication_date},
            "2026-10-29",
        )
    assert list(tmp_path.iterdir()) == []


@pytest.fixture
def raw_release(tmp_path):
    module = pipeline()
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    tables = {
        "eWellWARRawData.zip": ("eWellWARRawData/mv_war_main.txt", [activity()]),
        "BoreholeRawData.zip": ("BoreholeRawData/mv_boreholes_all.txt", [borehole()]),
        "eWellAPMRawData.zip": ("eWellAPMRawData/mv_apm_rig_view.txt", [rig()]),
        "eWellAPDRawData.zip": (
            "eWellAPDRawData/mv_apd_main.txt",
            [{"SN_APD": "42", "RIG_ID_NUM": "100", "RIG_TYPE_CODE": "JU"}],
        ),
        "rigidlistdelimit.zip": (
            "rigidlistdelimit.txt",
            [{"RIG_ID": "100", "RIG_NAME": "PUBLIC RIG", "RIG_TYPE": "JACKUP"}],
        ),
        "eWellEORRawData.zip": ("unused.txt", [{"ID": "1"}]),
    }
    source = {"sources": [], "publication_date": "2026-10-29"}
    for name, (member, records) in tables.items():
        buffer = io.StringIO(newline="\n")
        writer = csv.DictWriter(
            buffer, fieldnames=list(records[0]), lineterminator="\n"
        )
        if name != "rigidlistdelimit.zip":
            writer.writeheader()
        writer.writerows(records)
        archive_path = raw_dir / name
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr(member, buffer.getvalue().encode("utf-8"))
        entry = {
            "file": name,
            "url": module.SOURCES[name],
            "retrieved_at_utc": "2026-10-29T12:00:00+00:00",
            "sha256": hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            "size_bytes": archive_path.stat().st_size,
        }
        source["sources"].append(module.retain_blob(raw_dir, archive_path, entry))
    return raw_dir, source


@pytest.mark.parametrize("refresh", [False, True])
def test_reuse_manifest_cli_preserves_or_explicitly_refreshes_publication_date(
    tmp_path, monkeypatch, raw_release, refresh
):
    module = pipeline()
    raw_dir, source = raw_release
    manifest_path = tmp_path / "source.json"
    module.write_json(manifest_path, source)
    output = tmp_path / "release"
    argv = [
        "build_jackup_activity.py",
        "--raw-dir",
        raw_dir.as_posix(),
        "--reuse-manifest",
        manifest_path.as_posix(),
        "--output-dir",
        output.as_posix(),
    ]
    if refresh:
        argv += ["--publication-date", "2026-11-04"]
    monkeypatch.setattr("sys.argv", argv)
    module.main()
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["publication_date"] == ("2026-11-04" if refresh else "2026-10-29")
    assert len(module.verify_release(output)) == 1


@pytest.mark.parametrize("anomaly_count", [0, 2])
def test_refreshed_card_uses_audit_counts_and_exact_registry_evidence(
    tmp_path, anomaly_count
):
    module = pipeline()
    reports = [activity()]
    if anomaly_count:
        reports += [
            activity(SN_WAR="2", WATER_DEPTH="8831"),
            activity(SN_WAR="3", WATER_DEPTH="8831", RIG_NAME="UNMATCHED FIXTURE"),
        ]
    rows, counts = module.derive_table(reports, [borehole()], [rig()], [], [])
    manifest = module.write_release(
        tmp_path, rows, counts, {"sources": []}, "2026-10-29"
    )
    card = (tmp_path / "data_card.html").read_text(encoding="utf-8")
    assert f"8,831 ft source WAR records audited: {anomaly_count}." in card
    assert "nine" not in card
    assert "DS (drillship)" not in card
    audit = manifest["counts"]["source_8831_ft_record_audit"]
    if anomaly_count:
        assert audit[0]["registry_evidence"] == [{"rig_id": "100", "rig_type": "JU"}]
        assert audit[1]["registry_evidence"] == []
        assert "Exact-match registry evidence: rig 100 (JU)" in card
        assert "retained_flagged: 1" in card
        assert "unmatched_rig_name: 1" in card
    else:
        assert audit == []
        assert "Exact-match registry evidence: none" in card


def test_rig_names_are_only_used_for_matching_and_never_published(tmp_path):
    module = pipeline()
    rows, counts = module.derive_table(
        [activity(RIG_NAME=" public rig ", WATER_DEPTH="8831")],
        [borehole()],
        [rig()],
        [],
        [],
    )
    assert "rig_name" not in rows[0]
    assert rows[0]["rig_id"] == "100"
    assert counts["source_8831_ft_record_audit"][0]["rig_reference"] == "bsee-rig:100"
    module.write_release(tmp_path, rows, counts, {"sources": []}, "2026-10-29")
    for name in ("manifest.json", "data_card.html"):
        assert (
            "public rig" not in (tmp_path / name).read_text(encoding="utf-8").casefold()
        )
    raw = gzip.decompress((tmp_path / "activity_1997_2025.csv.gz").read_bytes())
    assert b"public rig" not in raw.lower()


def test_unmatched_reference_is_stable_across_order_case_and_spacing():
    module = pipeline()

    def audit(reports):
        return module.derive_table(reports, [borehole()], [rig()], [], [])[1][
            "source_8831_ft_record_audit"
        ]

    first = audit([activity(RIG_NAME="UNMATCHED FIXTURE", WATER_DEPTH="8831")])
    second = audit(
        [
            activity(SN_WAR="2"),
            activity(RIG_NAME=" unmatched fixture ", WATER_DEPTH="8831"),
        ]
    )
    assert first[0]["rig_reference"] == second[0]["rig_reference"]


@pytest.mark.parametrize("extra_liftboat", [False, True])
def test_card_identity_limits_are_derived_from_rows(tmp_path, extra_liftboat):
    module = pipeline()
    reports = [
        activity(),
        activity(SN_WAR="2", RIG_NAME="*GENERIC FIXTURE", WAR_START_DT="1/1/2005"),
        activity(SN_WAR="3", RIG_NAME="*GENERIC FIXTURE", WAR_START_DT="1/1/2006"),
    ]
    if extra_liftboat:
        reports.append(
            activity(SN_WAR="4", RIG_NAME="*OTHER FIXTURE", WAR_START_DT="1/1/2003")
        )
    rows, counts = module.derive_table(
        reports,
        [borehole()],
        [
            rig(),
            rig(RIG_ID_NUM="200", RIG_NAME="*GENERIC FIXTURE", RIG_TYPE_CODE="LB"),
            rig(RIG_ID_NUM="201", RIG_NAME="*OTHER FIXTURE", RIG_TYPE_CODE="LB"),
        ],
        [{"SN_APD": "42", "RIG_ID_NUM": "100", "RIG_TYPE_CODE": "DS"}],
        [],
    )
    # Stale supplied summaries must be replaced by statistics from the new table.
    counts["identity_by_rig_type"] = {"LB": {"distinct_ids": 999}}
    manifest = module.write_release(
        tmp_path, rows, counts, {"sources": []}, "2026-10-29"
    )
    card = (tmp_path / "data_card.html").read_text()
    for code, label in [("JU", "Jack-up"), ("LB", "Liftboat")]:
        group = [r for r in rows if r["rig_type"] == code]
        generic = sum(
            "generic_rig_identity" in r["quality_flags"].split("|") for r in group
        )
        checks = {
            status: sum(r["rig_type_check"] == status for r in group)
            for status in ("agree", "conflict", "unavailable")
        }
        first = min(r["activity_start_date"] for r in group)
        distinct = len({r["rig_id"] for r in group})
        assert manifest["counts"]["identity_by_rig_type"][code] == {
            "records": len(group),
            "distinct_ids": distinct,
            "generic_identity_records": generic,
            "secondary_evidence": checks,
            "first_report_year": int(first[:4]),
        }
        assert (
            f"{label}: {len(group):,} reports; {distinct:,} distinct IDs; "
            f"{generic:,} generic-identity reports; secondary evidence "
            f"agree {checks['agree']:,}, conflict {checks['conflict']:,}, "
            f"unavailable {checks['unavailable']:,}; first report year {first[:4]}."
        ) in card
    first_lb = min(r["activity_start_date"][:4] for r in rows if r["rig_type"] == "LB")
    assert (
        "All retained liftboat rows identify a generic placeholder, not an individual unit."
        in card
    )
    assert (
        f"Zero liftboat rows in years before {first_lb} are not evidence of no activity."
        in card
    )
    assert "Pre-spud move-in reports can end before the borehole spud date." in card


def test_changed_table_requires_explicit_refresh_date_before_any_write(tmp_path):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    source = module.write_release(
        tmp_path / "original", rows, counts, {"sources": []}, "2026-10-29"
    )
    rows[0]["water_depth_ft"] = "210"
    output = tmp_path / "changed"
    with pytest.raises(ValueError, match="publication-date"):
        module.write_release(output, rows, counts, source, "2026-10-29")
    assert not output.exists()
    refreshed = module.write_release(
        output, rows, counts, source, "2026-10-29", publication_date=date(2026, 11, 5)
    )
    assert refreshed["table"]["sha256"] != source["table"]["sha256"]


def test_refresh_appends_revision_without_redating_history(tmp_path):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    source = module.write_release(
        tmp_path / "original",
        rows,
        counts,
        {"sources": []},
        "2026-10-29",
        publication_date=date(2026, 11, 3),
    )
    previous = json.loads(json.dumps(source))
    refreshed = module.write_release(
        tmp_path / "refresh",
        rows,
        counts,
        source,
        "2026-10-29",
        publication_date=date(2026, 11, 5),
    )
    assert source == previous
    assert refreshed["revision_history"][:-1] == source["revision_history"]
    assert refreshed["revision_history"][-1]["date"] == "2026-11-05"
    assert (
        refreshed["revision_history"][-1]["revision"]
        == source["revision_history"][-1]["revision"] + 1
    )
    card = (tmp_path / "refresh" / "data_card.html").read_text()
    for row in refreshed["revision_history"]:
        assert f"<td>{row['date']}</td><td>{row['description']}</td>" in card


@pytest.mark.parametrize("invalid_date", ["not-a-date", "", None])
def test_build_validates_reused_date_before_creating_output(
    tmp_path, raw_release, invalid_date
):
    module = pipeline()
    raw_dir, source = raw_release
    source["publication_date"] = invalid_date
    output = tmp_path / "invalid-release"
    with pytest.raises((ValueError, TypeError)):
        module.build_release(raw_dir, source, output)
    assert not output.exists()


def test_manual_refresh_and_registered_catalog_only(tmp_path):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    manifest = module.write_release(
        tmp_path,
        rows,
        counts,
        {"sources": [], "next_refresh_date": "2026-10-30"},
        "2026-10-29",
    )
    assert "next_refresh_date" not in manifest
    assert manifest["refresh_basis"]["cadence"] == "manual"
    assert manifest["refresh_basis"]["source_cadence"] == "daily"
    assert manifest["refresh_basis"]["automatic"] is False
    assert manifest["source_ids"] == ["bsee-data-center"]
    card = (tmp_path / "data_card.html").read_text()
    assert "Refresh is manual; no refresh is scheduled." in card
    assert "Next planned refresh" not in card
    assert "bsee-ewell-war" not in card


@pytest.mark.parametrize("liftboat_kind", ["absent", "unit", "mixed"])
def test_refresh_does_not_repeat_blanket_placeholder_claim(tmp_path, liftboat_kind):
    module = pipeline()
    reports, rigs = [activity()], [rig()]
    if liftboat_kind != "absent":
        reports.append(
            activity(SN_WAR="2", RIG_NAME="UNIT FIXTURE", WAR_START_DT="1/1/2001")
        )
        rigs.append(rig(RIG_ID_NUM="200", RIG_NAME="UNIT FIXTURE", RIG_TYPE_CODE="LB"))
    if liftboat_kind == "mixed":
        reports.append(
            activity(SN_WAR="3", RIG_NAME="*GENERIC FIXTURE", WAR_START_DT="1/1/2002")
        )
        rigs.append(
            rig(RIG_ID_NUM="201", RIG_NAME="*GENERIC FIXTURE", RIG_TYPE_CODE="LB")
        )
    rows, counts = module.derive_table(reports, [borehole()], rigs, [], [])
    module.write_release(tmp_path, rows, counts, {"sources": []}, "2026-10-29")
    card = (tmp_path / "data_card.html").read_text()
    assert "All retained liftboat rows identify a generic placeholder" not in card
    if liftboat_kind == "absent":
        assert "first report year unavailable" in card
        assert (
            "No liftboat rows are retained; this is not evidence of no activity."
            in card
        )
    elif liftboat_kind == "mixed":
        assert (
            "Generic liftboat rows identify a placeholder, not an individual unit."
            in card
        )
    else:
        assert "first report year 2001" in card


def test_legacy_revision_dates_survive_migration_and_later_refresh(tmp_path):
    module = pipeline()
    rows, counts = module.derive_table([activity()], [borehole()], [rig()], [], [])
    legacy = module.write_release(
        tmp_path / "old",
        rows,
        counts,
        {"sources": []},
        "2026-10-29",
        publication_date=date(2026, 11, 3),
    )
    del legacy["revision_history"]
    refreshed = module.write_release(
        tmp_path / "new",
        rows,
        counts,
        legacy,
        "2026-10-29",
        publication_date=date(2026, 11, 5),
    )
    assert [(r["revision"], r["date"]) for r in refreshed["revision_history"]] == [
        (1, "2026-10-29"),
        (2, "2026-11-03"),
        (3, "2026-11-05"),
    ]
    again = module.write_release(
        tmp_path / "again",
        rows,
        counts,
        refreshed,
        "2026-10-29",
        publication_date=date(2026, 11, 6),
    )
    assert again["revision_history"][:-1] == refreshed["revision_history"]
