"""Review regressions for issue 1293; all quantities and clocks are synthetic."""

import json
from pathlib import PureWindowsPath
from types import SimpleNamespace

import pandas as pd
import pytest

from worldenergydata.scheduler.jobs.spain_cores_refresh import SpainCoresRefreshJob
from worldenergydata.spain.production.cores_live import CoresLiveProductionLoader
from worldenergydata.spain.production.cores_loader import (
    CoresParseError,
    extract_cores_field_names,
    parse_cores_frame,
)
from worldenergydata.spain.production.cores_source import (
    DEFAULT_WORKBOOKS,
    STATISTICS_PAGE_URL,
    CoresHttpResponse,
    CoresWorkbookSource,
)
from worldenergydata.spain.reports.cores_field_development import _field_summaries


@pytest.mark.parametrize("product", ["oil", "gas"])
@pytest.mark.parametrize("blank", [None, "", "-", "—", "..", "...", float("nan")])
def test_single_product_interior_blank_reaches_report(
    tmp_path, monkeypatch, product, blank
):
    """P2-1: [0, unknown, 10] has an unknown total, not 10 times a factor.

    Rows cross a year boundary and arrive out of order. A declared synthetic
    oil factor of 2 isolates parsing; no physical conversion is qualified.
    Leading/trailing blanks and an entirely blank field have no producing life.
    """
    raw = pd.DataFrame(
        {
            "Year": [2024, 2023, 2024, 2024, 2023],
            "Month": ["February", "November", "January", "March", "December"],
            "Field A": [10, blank, blank, blank, 0],
            "Field B": [blank] * 5,
        }
    )
    parsed = parse_cores_frame(
        raw,
        product=product,
        oil_conversion_audit=SimpleNamespace(bbl_per_tonne_for_field=lambda _: 2.0),
    ).sort_values(["year", "month"])
    assert parsed[["year", "month"]].values.tolist() == [
        [2023, 12],
        [2024, 1],
        [2024, 2],
    ]
    assert extract_cores_field_names(raw) == ["Field A"]
    column = "oil_bbl" if product == "oil" else "gas_mcf"
    assert parsed[column].iloc[0] == 0.0
    assert pd.isna(parsed[column].iloc[1])
    # Independent arithmetic with the declared synthetic oil factor: 10 * 2.
    if product == "oil":
        assert parsed[column].iloc[2] == 20.0

    loader = CoresLiveProductionLoader(cache_root=tmp_path)
    for candidate, value_column in (("oil", "oil_bbl"), ("gas", "gas_mcf")):
        frame = (
            parsed
            if candidate == product
            else pd.DataFrame(columns=["field_name", "year", "month", value_column])
        )
        monkeypatch.setattr(
            loader, f"load_{candidate}_production", lambda frame=frame: frame
        )
    item = _field_summaries(loader.load_all_production())[0]
    assert item["row_count"] == 3
    assert item[column] is None
    assert f"{column}_missing_observations" in item["limitations"]
    assert item["monthly"][1] == {"period": "2024-01", "oil_bbl": None, "gas_mcf": None}
    assert json.loads(json.dumps(item, allow_nan=False))[column] is None


@pytest.mark.parametrize("value", ["١٢٣", "１２３", "1.٢٣٤", "2,٥"])
@pytest.mark.parametrize("column", ["Year", "Field A"])
def test_numeric_text_rejects_non_ascii_digits(value, column):
    """Nit 4: CLDR's cited latn contract does not accept other digit systems."""
    raw = pd.DataFrame({"Year": [2024], "Month": ["January"], "Field A": [1]})
    raw[column] = [value]
    with pytest.raises(CoresParseError, match="invalid Spanish numeric text"):
        parse_cores_frame(raw, product="gas")


@pytest.mark.parametrize(
    "oil_time,gas_time,expected",
    [
        ("2026-01-01T00:00:00", "2026-02-01T00:00:00Z", "2026-01-01T00:00:00Z"),
        ("2026-01-01T00:30:00", "2026-01-01T01:00:00+02:00", "2025-12-31T23:00:00Z"),
        ("2026-02-01T00:00:00Z", "2026-01-01T00:00:00", "2026-01-01T00:00:00Z"),
    ],
)
def test_cached_acquisition_offsets_are_normalized(
    tmp_path, oil_time, gas_time, expected
):
    """Nit 5: legacy naive instants mean UTC; compare instants, not wall times."""
    source = CoresWorkbookSource(
        cache_root=tmp_path, clock=lambda: "2026-03-01T00:00:00Z"
    )
    source.raw_dir.mkdir()
    source.metadata_dir.mkdir()
    for workbook in DEFAULT_WORKBOOKS.values():
        (source.raw_dir / workbook.filename).write_bytes(b"synthetic cached workbook")
    source.metadata_path.write_text(
        json.dumps(
            {
                "workbooks": {
                    "oil": {"acquired_at_utc": oil_time},
                    "gas": {"acquired_at_utc": gas_time},
                }
            }
        ),
        encoding="utf-8",
    )
    source.download_all(validate_links=False)
    metadata = source.metadata()
    assert metadata["refreshed_at_utc"] == expected
    assert metadata["workbooks"]["oil"]["acquired_at_utc"] == oil_time
    assert metadata["workbooks"]["gas"]["acquired_at_utc"] == gas_time


@pytest.mark.parametrize("missing_header", [False, True])
def test_scheduler_content_vintage_survives_repeated_downloads(
    tmp_path, missing_header
):
    """Advisory 2/3: new acquisition cannot advance unchanged content vintage.

    Hand count per run: one statistics page plus two workbook GETs = three.
    Latest observed March precedes a trailing blank April. Complete-source
    publication date is the older workbook date, or unknown if one is absent.
    """
    now = ["2026-05-01T00:00:00Z"]
    calls = []

    def http_get(url, **kwargs):
        calls.append(url)
        if url == STATISTICS_PAGE_URL:
            links = "".join(
                f'<a href="{w.source_url}">data</a>' for w in DEFAULT_WORKBOOKS.values()
            )
            return CoresHttpResponse(content=links.encode(), headers={})
        last_modified = "Sun, 12 Apr 2026 00:00:00 GMT"
        if url == DEFAULT_WORKBOOKS["gas"].source_url:
            last_modified = None if missing_header else "Mon, 13 Apr 2026 00:00:00 GMT"
        headers = {} if last_modified is None else {"Last-Modified": last_modified}
        return CoresHttpResponse(content=b"synthetic workbook", headers=headers)

    source = CoresWorkbookSource(
        cache_root=tmp_path, http_get=http_get, clock=lambda: now[0]
    )

    class Loader:
        def __init__(self, **kwargs):
            pass

        def refresh(self, *, force_refresh):
            source.download_all(force_refresh=force_refresh)

        def metadata(self):
            return source.metadata()

        def load_all_production(self):
            return pd.DataFrame(
                {
                    "field_name": ["Field A"] * 3,
                    "year": [2026] * 3,
                    "month": [4, 1, 3],
                    "oil_bbl": [None, 1.0, 0.0],
                    "gas_mcf": [None, None, None],
                }
            )

    job = SpainCoresRefreshJob()
    monkey_loader = lambda: Loader
    job._loader_class = monkey_loader
    for acquired in ("2026-05-01T00:00:00Z", "2026-06-01T00:00:00Z"):
        now[0] = acquired
        assert job.run({"output_dir": tmp_path}).status == "success"
        metadata = json.loads((tmp_path / "_metadata.json").read_text(encoding="utf-8"))
        assert metadata["last_refresh"] == acquired
        assert metadata["latest_observation_period"] == "2026-03"
        assert metadata["source_updated_date"] == (
            None if missing_header else "2026-04-12"
        )
    assert len(calls) == 6


def test_scheduler_unknown_content_vintage_is_explicit(tmp_path):
    """Advisory 2: absent observation/publication evidence stays JSON null."""
    SpainCoresRefreshJob._write_refresh_metadata(tmp_path, 1, {})
    metadata = json.loads((tmp_path / "_metadata.json").read_text(encoding="utf-8"))
    assert metadata["latest_observation_period"] is None
    assert metadata["source_updated_date"] is None


def test_scheduler_metadata_paths_use_portable_separators(tmp_path, monkeypatch):
    """The reviewed Windows failure must retain the same CSV/sidecar assertions."""
    from worldenergydata.scheduler.jobs import spain_cores_refresh

    class File:
        def __init__(self, name):
            self.name = name
            self.suffix = "." + name.rsplit(".", 1)[1]

        def is_file(self):
            return True

        def stat(self):
            return SimpleNamespace(st_size=1)

        def relative_to(self, root):
            return PureWindowsPath("normalized") / self.name

    files = [File("production.csv"), File("audit.json")]
    monkeypatch.setattr(spain_cores_refresh, "current_output_files", lambda _: files)
    SpainCoresRefreshJob._write_refresh_metadata(tmp_path, 1, {})
    metadata = json.loads((tmp_path / "_metadata.json").read_text(encoding="utf-8"))
    assert metadata["files"] == ["normalized/production.csv"]
    assert metadata["sidecar_files"] == ["normalized/audit.json"]
    assert metadata["file_count"] == metadata["sidecar_file_count"] == 1
