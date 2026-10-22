"""Explicit UTC station-day retrieval and descriptive summaries, without fitting."""

from collections.abc import Sequence
from datetime import date, timedelta
from urllib.parse import urlencode

import httpx

from worldenergydata.metocean.clients.endpoint_checks import (
    EndpointError,
    Sample,
    probe_sample,
)
from worldenergydata.metocean.source_register import get_source


def fetch_station_day(
    source: str,
    station: str,
    day: date,
    *,
    http: httpx.Client,
    user_agent: str,
) -> list[Sample]:
    """Fetch NDBC recent text or a CO-OPS metric MLLW water-level day.

    NDBC's rolling realtime file must still contain the requested UTC day; this
    is not an arbitrary-date archive API. CO-OPS API defines begin/end dates,
    product, units, datum and time_zone (see the register's docs_url). Responses
    may be incomplete or contain missing observations; no gaps are filled.
    """
    if not station or not station.isascii() or not station.isalnum():
        raise ValueError("An ASCII alphanumeric station identifier is required")
    if type(day) is not date:
        raise ValueError("A UTC calendar date is required")
    if source == "ndbc_realtime":
        url = f'{get_source(source)["base_url"]}/data/realtime2/{station}.txt'
    elif source == "coops":
        if not station.isdigit():
            raise ValueError("A numeric CO-OPS station identifier is required")
        query = urlencode(
            {
                "station": station,
                "begin_date": day.strftime("%Y%m%d"),
                "end_date": day.strftime("%Y%m%d"),
                "product": "water_level",
                "units": "metric",
                "time_zone": "gmt",
                "datum": "MLLW",
                "format": "json",
                "application": "metocean-example",
            }
        )
        url = f'{get_source(source)["base_url"]}/datagetter?{query}'
    else:
        raise ValueError("Station-day retrieval supports ndbc_realtime or coops")
    rows = probe_sample(source, http=http, user_agent=user_agent, url=url)
    if any(row.station != station for row in rows):
        raise EndpointError(f"{source}: response station does not match request")
    selected = [row for row in rows if row.timestamp.date() == day]
    if not selected:
        raise EndpointError(
            f"{source}: requested station-day not available in response"
        )
    return selected


def summarize_day(rows: Sequence[Sample]) -> dict:
    """Count received/missing values and retain first/last valid UTC observations.

    Counts are descriptive only, not completeness or quality acceptance limits.
    Source precision is preserved. No averaging, interpolation or unit conversion
    is performed. NDBC WVHT and CO-OPS MLLW water level are different quantities.
    """
    if not rows:
        raise ValueError("Cannot summarize an empty station-day")
    first = rows[0]

    def key(row):
        return (
            row.source,
            row.station,
            row.timestamp.date(),
            row.variable,
            row.unit,
            row.datum,
        )

    if any(
        key(row) != key(first) or row.timestamp.utcoffset() != timedelta(0)
        for row in rows
    ):
        raise ValueError("Summary requires a single UTC station-day and variable")
    valid = sorted(
        (row for row in rows if row.value is not None), key=lambda row: row.timestamp
    )
    return {
        "source": first.source,
        "station": first.station,
        "date": first.timestamp.date().isoformat(),
        "variable": first.variable,
        "unit": first.unit,
        "datum": first.datum,
        "rows": len(rows),
        "nonmissing": len(valid),
        "first_utc": valid[0].timestamp.isoformat() if valid else None,
        "first_value": valid[0].value if valid else None,
        "last_utc": valid[-1].timestamp.isoformat() if valid else None,
        "last_value": valid[-1].value if valid else None,
    }
