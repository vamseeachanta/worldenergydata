"""Tests for WTI prices helper functions."""

import csv
import hashlib
import json
import logging
import runpy
from io import StringIO
from pathlib import Path
from typing import Any, Callable, Iterator, NoReturn, cast

import pandas as pd
import pytest

from worldenergydata.lower_tertiary import wti_prices
from worldenergydata.lower_tertiary.wti_prices import (
    V30_LAST_MONTH,
    V30_LAST_PRICE,
    _append,
    _covered_periods,
    _needed_months,
    get_wti_source_summary,
)


class TestConstants:
    def test_v30_last_price(self):
        assert V30_LAST_PRICE == 68.39

    def test_v30_last_month(self):
        assert V30_LAST_MONTH == pd.Timestamp("2025-07-01")


class TestCoveredPeriods:
    def test_none(self):
        assert _covered_periods(None) == set()

    def test_empty(self):
        df = pd.DataFrame({"Month": pd.DatetimeIndex([])})
        assert _covered_periods(df) == set()

    def test_basic(self):
        df = pd.DataFrame({"Month": pd.to_datetime(["2025-08-01", "2025-09-01"])})
        result = _covered_periods(df)
        assert len(result) == 2
        assert pd.Period("2025-08", "M") in result
        assert pd.Period("2025-09", "M") in result


class TestNeededMonths:
    def test_basic(self):
        result = _needed_months(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-10-01"))
        assert len(result) == 3
        assert result[0] == pd.Timestamp("2025-08-01")
        assert result[1] == pd.Timestamp("2025-09-01")
        assert result[2] == pd.Timestamp("2025-10-01")

    def test_same_month(self):
        result = _needed_months(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-07-01"))
        assert len(result) == 0

    def test_single_month(self):
        result = _needed_months(pd.Timestamp("2025-07-01"), pd.Timestamp("2025-08-01"))
        assert len(result) == 1
        assert result[0] == pd.Timestamp("2025-08-01")


class TestAppend:
    def test_none_base(self):
        new = pd.DataFrame({"a": [1, 2]})
        result = _append(None, new)
        assert len(result) == 2

    def test_with_base(self):
        base = pd.DataFrame({"a": [1]})
        new = pd.DataFrame({"a": [2, 3]})
        result = _append(base, new)
        assert len(result) == 3

    def test_reset_index(self):
        base = pd.DataFrame({"a": [1]}, index=[5])
        new = pd.DataFrame({"a": [2]}, index=[10])
        result = _append(base, new)
        assert list(result.index) == [0, 1]


class TestGetWtiSourceSummary:
    def test_all_sources(self):
        df = pd.DataFrame(
            {
                "source": [
                    "v30_xlsx",
                    "v30_xlsx",
                    "local_snapshot",
                    "eia_github",
                    "fred_api",
                    "flat_forward",
                    "flat_forward",
                ],
            }
        )
        result = get_wti_source_summary(df)
        assert result["v30_xlsx"] == 2
        assert result["local_snapshot"] == 1
        assert result["eia_github"] == 1
        assert result["fred_api"] == 1
        assert result["flat_forward"] == 2

    def test_missing_sources_zero(self):
        df = pd.DataFrame({"source": ["v30_xlsx"]})
        result = get_wti_source_summary(df)
        assert result["local_snapshot"] == 0
        assert result["eia_github"] == 0
        assert result["fred_api"] == 0
        assert result["flat_forward"] == 0

    def test_includes_all_keys(self):
        df = pd.DataFrame({"source": []})
        result = get_wti_source_summary(df)
        assert set(result.keys()) == {
            "v30_xlsx",
            "local_snapshot",
            "eia_github",
            "fred_api",
            "flat_forward",
        }


@pytest.fixture(autouse=True)
def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """All tests are offline, including fallback and emitter tests."""

    def blocked(*args: Any, **kwargs: Any) -> NoReturn:
        raise AssertionError("Network is blocked in WTI tests")

    monkeypatch.setattr(wti_prices.requests, "get", blocked)
    monkeypatch.delenv("FRED_API_KEY", raising=False)


@pytest.fixture
def synthetic_v30(monkeypatch: pytest.MonkeyPatch) -> None:
    """Synthetic baseline isolates cascade tests from unrelated input stores."""
    baseline = pd.DataFrame({"Month": [pd.Timestamp("2025-07-01")], "WTI_USD": [68.39]})
    monkeypatch.setattr(wti_prices, "_load_v30", lambda: baseline)


class TestLocalSnapshot:
    def test_committed_snapshot_coverage_and_overlap(self) -> None:
        snapshot = wti_prices.LOCAL_SNAPSHOT_PATH
        assert snapshot.is_file()
        raw = wti_prices._parse_wti_csv(
            snapshot, pd.Timestamp("1900-01-01"), pd.Timestamp("2100-01-01")
        )
        assert list(raw.columns) == ["Month", "WTI_USD"]
        assert len(raw) > 400
        july = raw.loc[raw["Month"] == V30_LAST_MONTH, "WTI_USD"].item()
        assert abs(july - V30_LAST_PRICE) < 0.01
        expected = set(pd.period_range("2025-08", "2026-04", freq="M"))
        assert expected <= _covered_periods(raw)

    @pytest.mark.parametrize("synthetic", [False, True], ids=["real", "synthetic"])
    def test_real_v30_offline_extension(
        self, monkeypatch: pytest.MonkeyPatch, synthetic: bool
    ) -> None:
        """Workbook values take precedence; synthetic input exercises extension."""
        workbook = wti_prices.load_v30_wti_prices().copy()
        snapshot = wti_prices._parse_wti_csv(
            wti_prices.LOCAL_SNAPSHOT_PATH,
            pd.Timestamp("1900-01-01"),
            pd.Timestamp("2100-01-01"),
        )
        through = pd.Timestamp("2026-04-01")
        if synthetic:
            # Synthetic workbook ends before the requested snapshot window.
            workbook = workbook[workbook["Month"] < through].tail(2).copy()
            workbook["WTI_USD"] = [10.0, 20.0]
            monkeypatch.setattr(wti_prices, "_load_v30", lambda: workbook)

        def unexpected(*args: Any) -> None:
            pytest.fail("A complete snapshot must not invoke network fallbacks")

        monkeypatch.setattr(wti_prices, "_fetch_eia_github_prices", unexpected)
        monkeypatch.setattr(wti_prices, "_fetch_fred_prices", unexpected)
        result = wti_prices.load_extended_wti_prices(str(through.date()))
        requested = result[result["Month"] <= through].set_index("Month")
        expected_workbook = workbook[workbook["Month"] <= through].set_index("Month")
        expected_snapshot = snapshot[
            (snapshot["Month"] > workbook["Month"].max())
            & (snapshot["Month"] <= through)
        ].set_index("Month")
        local = requested[requested["source"] == "local_snapshot"]
        assert set(local.index).isdisjoint(workbook["Month"])
        assert set(local.index) == set(expected_snapshot.index)
        assert set(requested.index) == set(expected_workbook.index) | set(local.index)
        for month, row in expected_workbook.iterrows():
            assert requested.loc[month, "WTI_USD"] == row["WTI_USD"]
            assert requested.loc[month, "source"] == "v30_xlsx"
        for month, row in expected_snapshot.iterrows():
            assert local.loc[month, "WTI_USD"] == row["WTI_USD"]
        assert get_wti_source_summary(result)["flat_forward"] == 0
        if synthetic:
            assert not expected_snapshot.empty

    def test_no_month_supplied_by_both_sources_with_different_values(self) -> None:
        """Compare every real overlap month using the existing price tolerance."""
        workbook = wti_prices.load_v30_wti_prices().set_index("Month")["WTI_USD"]
        snapshot = wti_prices._parse_wti_csv(
            wti_prices.LOCAL_SNAPSHOT_PATH,
            pd.Timestamp("1900-01-01"),
            pd.Timestamp("2100-01-01"),
        ).set_index("Month")["WTI_USD"]
        overlap = workbook.index.intersection(snapshot.index)
        assert not overlap.empty
        conflicts = [
            (
                month.strftime("%Y-%m"),
                workbook[month],
                snapshot[month],
                workbook[month] - snapshot[month],
            )
            for month in overlap
            if abs(workbook[month] - snapshot[month]) > 0.01
        ]
        assert not conflicts, f"Workbook/snapshot price conflicts: {conflicts}"

    @pytest.mark.parametrize("content", [None, "synthetic invalid CSV\n"])
    def test_missing_or_corrupt_snapshot_warns(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
        caplog: pytest.LogCaptureFixture,
        synthetic_v30: None,
        content: str | None,
    ) -> None:
        snapshot = tmp_path / "synthetic-wti.csv"
        if content is not None:
            snapshot.write_text(content)
        monkeypatch.setattr(wti_prices, "LOCAL_SNAPSHOT_PATH", snapshot)
        with caplog.at_level(logging.WARNING):
            result = wti_prices.load_extended_wti_prices("2026-04-01")
        assert get_wti_source_summary(result)["flat_forward"] == 9
        assert "data/wti-monthly.PROVENANCE.md" in caplog.text
        assert "refresh data/wti-monthly.csv" in caplog.text

    def test_partial_snapshot_keeps_local_values(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, synthetic_v30: None
    ) -> None:
        snapshot = tmp_path / "synthetic-wti.csv"
        snapshot.write_text("Date,Price\n2025-08-15,10\n")
        monkeypatch.setattr(wti_prices, "LOCAL_SNAPSHOT_PATH", snapshot)
        fetched = pd.DataFrame(
            {
                "Month": pd.to_datetime(["2025-08-01", "2025-09-01"]),
                "WTI_USD": [99.0, 20.0],
                "source": ["eia_github"] * 2,
            }
        )
        monkeypatch.setattr(wti_prices, "_fetch_eia_github_prices", lambda *a: fetched)
        result = wti_prices.load_extended_wti_prices("2025-10-01")
        assert list(result["WTI_USD"]) == [68.39, 10.0, 20.0, 68.39]
        assert list(result["source"])[1:] == [
            "local_snapshot",
            "eia_github",
            "flat_forward",
        ]

    def test_parser_normalizes_and_filters_synthetic_rows(self) -> None:
        raw = StringIO(
            " Date , Price \n2025-07-15,68.39\n2025-08-15,10\n"
            "2025-09-15,invalid\n2025-10-15,30\n"
        )
        result = wti_prices._parse_wti_csv(
            raw, V30_LAST_MONTH, pd.Timestamp("2025-09-01")
        )
        assert list(result["Month"]) == [pd.Timestamp("2025-08-01")]
        assert list(result["WTI_USD"]) == [10.0]


class TestWtiInputGuard:
    @pytest.fixture
    def loader(self) -> Callable[[str | None], pd.DataFrame]:
        path = Path(wti_prices.__file__).resolve().parents[5] / (
            "docs/modules/bsee/analysis/production/FDAS_V30/"
            "ogora_to_chronological.py"
        )
        return cast(
            Callable[[str | None], pd.DataFrame],
            runpy.run_path(str(path))["load_wti_monthly"],
        )

    def test_omitted_path(self, loader: Callable[[str | None], pd.DataFrame]) -> None:
        assert list(loader(None).columns) == ["MONTH", "WTI_USD"]
        assert loader(None).empty

    def test_missing_explicit_path(
        self, loader: Callable[[str | None], pd.DataFrame], tmp_path: Path
    ) -> None:
        with pytest.raises(FileNotFoundError, match="data/wti-monthly.csv"):
            loader(str(tmp_path / "synthetic-missing.csv"))

    def test_committed_snapshot_is_consumable(
        self, loader: Callable[[str | None], pd.DataFrame]
    ) -> None:
        assert len(loader(str(wti_prices.LOCAL_SNAPSHOT_PATH))) > 400


class TestProvenance:
    def test_committed_parsed_values_hash_and_row_count(self) -> None:
        snapshot = wti_prices.LOCAL_SNAPSHOT_PATH
        with snapshot.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.reader(stream))
        digest = hashlib.sha256(
            json.dumps(rows, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        sidecar = snapshot.with_suffix(".PROVENANCE.md").read_text()
        assert len(rows) - 1 == 489
        assert f"({len(rows) - 1} rows)" in sidecar
        assert f"Parsed-values SHA-256 as retrieved: `{digest}`" in sidecar
        assert f"Parsed-values SHA-256 as committed: `{digest}`" in sidecar

    def test_committed_snapshot_has_no_cr_bytes(self) -> None:
        assert b"\r" not in wti_prices.LOCAL_SNAPSHOT_PATH.read_bytes()

    def test_emitter_reproduces_committed_sidecar(self) -> None:
        snapshot = wti_prices.LOCAL_SNAPSHOT_PATH
        sidecar = snapshot.with_suffix(".PROVENANCE.md").read_text()
        metadata = json.loads(sidecar.split("```json\n", 1)[1].split("\n```", 1)[0])
        assert (
            wti_prices.emit_wti_provenance(snapshot.read_bytes(), metadata) == sidecar
        )

    def test_emitter_computes_synthetic_difference_and_digest(self) -> None:
        import hashlib

        payload = b"Date,Price\n2025-07-15,68.39\n2025-08-15,10\n"
        metadata = {
            "fixture_kind": "synthetic",
            "eia_observations_usd_per_barrel": {"2025-08": 12.0},
        }
        result = wti_prices.emit_wti_provenance(payload, metadata)
        assert hashlib.sha256(payload).hexdigest() in result
        assert "| 2025-08 | 10.00 | 12.00 | -2.00 |" in result
        assert "synthetic" in result


class TestBoundedMirrorFetch:
    def test_size_limit_and_response_close(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class SyntheticResponse:
            def __enter__(self) -> "SyntheticResponse":
                return self

            def __exit__(self, *args: object) -> None:
                self.closed = True

            def raise_for_status(self) -> None:
                pass

            def iter_content(self, chunk_size: int) -> Iterator[bytes]:
                yield b"x" * (wti_prices.MAX_CSV_BYTES + 1)

        response = SyntheticResponse()
        monkeypatch.setattr(wti_prices.requests, "get", lambda *a, **k: response)
        monkeypatch.setattr(wti_prices.time, "sleep", lambda seconds: None)
        with pytest.raises(ValueError, match="limit"):
            wti_prices._download_wti_csv()
        assert response.closed

    def test_timeout_agent_and_pause(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls: list[dict[str, Any]] = []

        class SyntheticResponse:
            def __enter__(self) -> "SyntheticResponse":
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def raise_for_status(self) -> None:
                pass

            def iter_content(self, chunk_size: int) -> Iterator[bytes]:
                yield b"Date,Price\n2025-08-15,10\n"

        def get(url: str, **kwargs: Any) -> SyntheticResponse:
            calls.append(kwargs)
            return SyntheticResponse()

        sleeps: list[int] = []
        monkeypatch.setattr(wti_prices.requests, "get", get)
        monkeypatch.setattr(wti_prices.time, "sleep", sleeps.append)
        assert wti_prices._download_wti_csv().startswith(b"Date,Price")
        assert sleeps == [2]
        assert calls[0]["timeout"] == 15
        assert calls[0]["stream"] is True
        assert "https://api.github.com/repositories/574746314" in (
            calls[0]["headers"]["User-Agent"]
        )
