"""Observed wave percentiles on original UTC rows, without temporal resampling.

Source-invalid values must be null. No additional range filter, source merging,
regular time grid, or peak/dominant conversion is applied. Callers must select
one active version per source file before passing a stream of normalised rows.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping

PERCENTILES = (50, 75, 90, 95, 99)
EXPECTED_UNITS = {"wave_height_m": "m", "wave_period_s": "s"}
PERIOD_KINDS = {"dominant", "peak"}
_BITS = {"height": 1, "dominant": 2, "peak": 4}


def _ordered_percentile(ordered: list[float], fraction: float) -> float | None:
    if not ordered:
        return None
    rank = fraction * (len(ordered) - 1)
    lower = math.floor(rank)
    upper = math.ceil(rank)
    return ordered[lower] + (rank - lower) * (ordered[upper] - ordered[lower])


def percentile(values: Iterable[float], fraction: float) -> float | None:
    """Interpolate sorted values at the zero-based rank p * (n - 1)."""
    if not math.isfinite(fraction) or not 0 <= fraction <= 1:
        raise ValueError("Percentile fraction must be finite and within [0, 1]")
    ordered = sorted(float(value) for value in values)
    if any(not math.isfinite(value) for value in ordered):
        raise ValueError("Percentile values must be finite")
    return _ordered_percentile(ordered, fraction)


def _utc(value: Any) -> datetime:
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError("Observation timestamp must carry a timezone")
    return value.astimezone(timezone.utc)


@dataclass(slots=True)
class _Sample:
    time: datetime
    present: int = 0
    height: float | None = None
    dominant: float | None = None
    peak: float | None = None


def _group_samples(records: Iterable[Mapping[str, Any]]) -> dict:
    """Retain one compact sample per source-file row; consume input once."""
    groups = defaultdict(dict)
    digests = {}
    for row in records:
        variable = row.get("variable")
        if variable not in EXPECTED_UNITS:
            continue
        if row.get("unit") != EXPECTED_UNITS[variable]:
            raise ValueError(f"Unexpected unit for {variable}")
        for name in ("station_id", "source_id", "raw_sha256"):
            if not isinstance(row.get(name), str) or not row[name]:
                raise ValueError(f"Missing or invalid {name}")
        number = row.get("row_number")
        if isinstance(number, bool) or not isinstance(number, int) or number < 0:
            raise ValueError("row_number must be a nonnegative integer")
        kind = row.get("period_kind") if variable == "wave_period_s" else "height"
        if variable == "wave_period_s" and kind not in PERIOD_KINDS:
            raise ValueError("wave_period_s requires dominant or peak period_kind")
        value = row.get("value")
        if value is not None:
            value = float(value)
            if not math.isfinite(value):
                raise ValueError("Observation value must be finite or null")
            if value < 0 or (variable == "wave_period_s" and value == 0):
                raise ValueError("Wave height must be nonnegative and period positive")
        timestamp = _utc(row.get("observation_time"))
        # Arrow materialises repeated strings separately; retain one digest string.
        digest = digests.setdefault(row["raw_sha256"], row["raw_sha256"])
        samples = groups[(row["station_id"], row["source_id"])]
        identity = (digest, number)
        sample = samples.get(identity)
        if sample is None:
            sample = _Sample(timestamp)
            samples[identity] = sample
        elif sample.time != timestamp:
            raise ValueError("Paired source row has inconsistent timestamp")
        bit = _BITS[kind]
        if sample.present & bit:
            raise ValueError("Duplicate source file row identity")
        sample.present |= bit
        setattr(sample, kind, value)
    return groups


def _summary(
    samples: Iterable[_Sample],
    station: str,
    source: str,
    kind: str,
    season: str,
    months: set[int],
) -> dict:
    heights = []
    periods = []
    height_missing = period_missing = 0
    years = set()
    first = latest = None
    period_bit = _BITS.get(kind, 0)
    # Keep only references to samples within this season for the paired-band pass.
    seasonal = []
    for sample in samples:
        if sample.time.month not in months:
            continue
        seasonal.append(sample)
        if sample.present & _BITS["height"]:
            if sample.height is None:
                height_missing += 1
            else:
                heights.append(sample.height)
                years.add(sample.time.year)
                first = sample.time if first is None else min(first, sample.time)
                latest = sample.time if latest is None else max(latest, sample.time)
        if sample.present & period_bit:
            value = getattr(sample, kind)
            if value is None:
                period_missing += 1
            else:
                periods.append(value)
    heights.sort()
    periods.sort()
    result = {
        "station_id": station,
        "source_id": source,
        "period_kind": kind,
        "season": season,
        "height_valid_count": len(heights),
        "height_missing_count": height_missing,
        "period_valid_count": len(periods),
        "period_missing_count": period_missing,
        "contributing_years": len(years),
        "first_timestamp": first.isoformat() if first else None,
        "latest_timestamp": latest.isoformat() if latest else None,
    }
    for point in PERCENTILES:
        result[f"height_p{point}_m"] = _ordered_percentile(heights, point / 100)
        result[f"period_p{point}_s"] = _ordered_percentile(periods, point / 100)
    height_95 = result["height_p95_m"]
    lower = height_95 - 0.25 if height_95 is not None else None
    upper = height_95 + 0.25 if height_95 is not None else None
    paired = []
    band_count = 0
    if height_95 is not None:
        for sample in seasonal:
            if sample.height is None or not lower <= sample.height <= upper:
                continue
            band_count += 1
            if sample.present & period_bit:
                value = getattr(sample, kind)
                if value is not None:
                    paired.append(value)
    paired.sort()
    counts = Counter(paired)
    mode = min(counts, key=lambda value: (-counts[value], value)) if counts else None
    result.update(
        {
            "band_lower_m": lower,
            "band_upper_m": upper,
            "band_height_count": band_count,
            "band_paired_count": len(paired),
            "band_period_mode_s": mode,
            "band_period_p10_s": _ordered_percentile(paired, 0.1),
            "band_period_p90_s": _ordered_percentile(paired, 0.9),
        }
    )
    return result


def summarize_observations(
    records: Iterable[Mapping[str, Any]], *, unique_timestamps: bool = False
) -> list[dict]:
    """Return fourteen seasonal tables per station, source and period kind.

    Sources and peak/dominant periods remain separate. Heights may contribute
    to both period kinds when explicitly provided. Empty months have zero
    counts and null statistics. Pairing uses source-file digest and row number;
    repeated timestamps in distinct archive rows remain distinct samples.
    An input generator permits one Arrow partition to be read at a time.
    For the explicit unique-timestamp comparison, the first valid height at
    each timestamp is retained with its paired periods. Input file order
    determines precedence. Original rows remain unchanged in the store.
    """
    groups = _group_samples(records)
    seasons = [("all", set(range(1, 13)))]
    seasons.extend((f"month_{month:02d}", {month}) for month in range(1, 13))
    seasons.append(("oct_mar", {10, 11, 12, 1, 2, 3}))
    result = []
    for (station, source), samples in sorted(groups.items()):
        if unique_timestamps:
            selected = {}
            for sample in samples.values():
                previous = selected.get(sample.time)
                if previous is None or (
                    previous.height is None and sample.height is not None
                ):
                    selected[sample.time] = sample
            samples = selected
        presence = 0
        for sample in samples.values():
            presence |= sample.present
        kinds = [kind for kind in sorted(PERIOD_KINDS) if presence & _BITS[kind]]
        for kind in kinds or ["not_available"]:
            for season, months in seasons:
                result.append(
                    _summary(samples.values(), station, source, kind, season, months)
                )
    return result
