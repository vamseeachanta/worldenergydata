"""Site climate contracts exercised with synthetic wave observations."""

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pytest

from worldenergydata.metocean.database.archive_store import ArchiveStore
from worldenergydata.metocean.site_climate import build_site_climate_index

FIRST_SET = Path(__file__).resolve().parents[3] / "data/modules/metocean/first_set.json"
JAN = datetime(2024, 1, 1, tzinfo=timezone.utc)
JUL = datetime(2024, 7, 1, tzinfo=timezone.utc)


def build(rows, regions, **options):
    return build_site_climate_index(
        rows,
        regions,
        station_metadata=json.loads(FIRST_SET.read_text("utf-8")),
        **options,
    )


def height(value, digest="a" * 64, station="42001", source="ndbc_archive", time=JAN):
    return {
        "station_id": station,
        "source_id": source,
        "row_number": 0,
        "observation_time": time,
        "raw_sha256": digest,
        "variable": "wave_height_m",
        "unit": "m",
        "period_kind": None,
        "value": value,
        "quality_flag": "synthetic",
    }


def period(row, kind, value):
    return dict(row, variable="wave_period_s", unit="s", period_kind=kind, value=value)


def summary(entry, kind="dominant", season="all"):
    return next(
        row
        for row in entry["summaries"]
        if (row["period_kind"], row["season"]) == (kind, season)
    )


@pytest.fixture
def synthetic_partitions(tmp_path):
    store = ArchiveStore(tmp_path / "synthetic")
    partitions = []
    for label, wave, kinds in [
        ("winter", height(1), {"dominant": 7, "peak": 10}),
        ("summer", height(3, time=JUL), {"dominant": 9}),
        ("second-source", height(12, source="ndbc_realtime"), {"peak": 14}),
        ("second-station", height(5, station="42002"), {"dominant": 11}),
    ]:
        entry = store.capture(
            wave["source_id"],
            wave["station_id"],
            label,
            f"synthetic {label}".encode(),
            {"terms_quote": "Synthetic fixture"},
        )
        wave["raw_sha256"] = entry["sha256"]
        store.normalize(entry, [wave] + [period(wave, k, v) for k, v in kinds.items()])
        partitions.append(entry)
    rows = [row for entry in partitions for row in store.read_rows(entry)]
    return rows, partitions


def test_verified_partitions_keep_regions_stations_sources_and_periods_separate(
    synthetic_partitions,
):
    rows, partitions = synthetic_partitions
    regions = {"42001": "west", "42002": "east"}
    metadata = json.loads(FIRST_SET.read_text("utf-8"))
    original = deepcopy((rows, regions, metadata))
    result = build_site_climate_index(iter(rows), regions, station_metadata=metadata)
    assert result == build(iter(rows), regions)
    assert (rows, regions, metadata) == original
    assert result["schema_version"] == 1
    assert result["readiness"] == "observations_only"
    assert result["duplicate_policy"] == "original_rows"
    east, west, realtime = result["entries"]
    assert [
        (e["region"], e["station_id"], e["source_id"]) for e in result["entries"]
    ] == [
        ("east", "42002", "ndbc_archive"),
        ("west", "42001", "ndbc_archive"),
        ("west", "42001", "ndbc_realtime"),
    ]
    assert west["input_raw_sha256"] == sorted(p["sha256"] for p in partitions[:2])
    assert east["input_raw_sha256"] == [partitions[3]["sha256"]]
    assert realtime["input_raw_sha256"] == [partitions[2]["sha256"]]
    assert summary(east)["height_p50_m"] == 5
    assert summary(realtime, "peak")["height_p50_m"] == 12
    assert len(west["summaries"]) == 28
    annual = summary(west)
    assert annual["height_p95_m"] == pytest.approx(2.9)
    assert annual["period_p50_s"] == 8
    assert (annual["first_timestamp"], annual["latest_timestamp"]) == (
        JAN.isoformat(),
        JUL.isoformat(),
    )
    assert summary(west, "peak")["period_p50_s"] == 10
    assert summary(west, season="oct_mar")["height_p50_m"] == 1
    assert summary(west, season="month_02")["height_p50_m"] is None
    shared = build(rows, dict.fromkeys(regions, "shared"))["entries"]
    assert len(shared) == 3
    assert [e["region"] for e in shared] == ["shared"] * 3


def test_order_controls_the_unique_timestamp_comparison():
    rows = [height(None), height(4, "b" * 64), height(8, "c" * 64)]
    rows = [
        item
        for row, tp in zip(rows, [13, 9, 11])
        for item in (row, period(row, "peak", tp))
    ]
    regions = {"42001": "west"}
    original = summary(build(rows, regions)["entries"][0], "peak")
    assert (original["height_valid_count"], original["height_p50_m"]) == (2, 6)
    for ordered, hs, tp in [(rows, 4, 9), (list(reversed(rows)), 8, 11)]:
        index = build(ordered, regions, unique_timestamps=True)
        assert index["duplicate_policy"] == "unique_timestamps"
        entry = index["entries"][0]
        assert entry["input_raw_sha256"] == [c * 64 for c in "abc"]
        chosen = summary(entry, "peak")
        assert (chosen["height_valid_count"], chosen["height_p50_m"]) == (1, hs)
        assert chosen["band_period_mode_s"] == tp


def test_text_cannot_enable_timestamp_deduplication():
    with pytest.raises(ValueError, match="unique_timestamps"):
        build([height(2)], {"42001": "west"}, unique_timestamps="false")


def test_empty_input_has_no_station_coverage():
    assert build([], {"42001": "west"})["entries"] == []


@pytest.mark.parametrize(
    "rows,regions,message",
    [
        ([height(2)], {}, "region"),
        ([], {"unknown": "west"}, "station"),
        ([], {"42001": "  "}, "region"),
        ([height(2, source="unknown")], {"42001": "west"}, "source"),
        ([height(2, source="ncep_wave_hindcast")], {"42001": "west"}, "source"),
        ([dict(height(2), variable="wind")], {"42001": "west"}, "variable"),
        ([dict(height(2), unit="ft")], {"42001": "west"}, "unit"),
    ],
)
def test_invalid_inputs_fail_explicitly(rows, regions, message):
    with pytest.raises(ValueError, match=message):
        build(rows, regions)


@pytest.mark.parametrize("digest", [None, "", "a" * 63, "g" * 64, "a" * 64 + "\n"])
def test_invalid_digest_rejected(digest):
    with pytest.raises(ValueError, match="raw_sha256"):
        build([height(1, digest)], {"42001": "west"})


def test_hex_case_cannot_split_one_source_row():
    wave = height(2, "A" * 64)
    paired = dict(period(wave, "dominant", 8), raw_sha256="a" * 64)
    entry = build([wave, paired], {"42001": "west"})["entries"][0]
    assert entry["input_raw_sha256"] == ["a" * 64]
    assert summary(entry)["band_paired_count"] == 1
