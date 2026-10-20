# ABOUTME: BSEE historical batch campaign detector for WRK-219.
# ABOUTME: Heuristic: same rig + same field/block within time window = batch.

"""Auditable activity grouping and log-space learning-factor fitting.

See ``docs/detector-contract.md`` for parsing, disposition and policy contracts.
The report APIs retain every input row's disposition. Compatibility wrappers
return the original types and log warnings when dispositions are discarded.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime
from numbers import Integral, Real

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {"well_id", "rig_name", "field_name", "spud_date"}
_FIT_COLUMNS = {"well_position", "days_to_drill"}
_NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_DATE = re.compile(
    r"[0-9]{4}-[0-9]{2}-[0-9]{2}"
    r"(?:[T ][0-9]{2}:[0-9]{2}(?::[0-9]{2}(?:\.[0-9]{1,9})?)?"
    r"(?:Z|[+-][0-9]{2}:[0-9]{2})?)?"
)

# Compatibility assumptions only; not empirically qualified drilling limits.
# Source: repository detector at b1394197a66f95d78615425b4e1ad4ff78bd9de2,
# lines 38-41 (window), 138-140 (default), 159-160 (inclusive clipping).
_LEGACY_MONTHS = 12
_LEGACY_DEFAULT = 0.85
_LEGACY_BOUNDS = (0.5, 1.0)


@dataclass(frozen=True)
class Reconciliation:
    """One positional row number, status and primary reason per input row."""

    rows: pd.DataFrame

    @property
    def counts(self) -> dict[str, int]:
        return {
            status: int(self.rows["status"].eq(status).sum())
            for status in ("accepted", "rejected", "excluded")
        }


@dataclass(frozen=True)
class BatchDetectionResult:
    batches: pd.DataFrame
    reconciliation: Reconciliation


@dataclass(frozen=True)
class LearningFitResult:
    factor: float | None
    raw_factor: float | None
    slope: float | None
    status: str
    reason: str
    reconciliation: Reconciliation


class BSEEBatchDetector:
    """Group unique spud events and fit individual observed durations.

    Windows are inclusive calendar-month offsets anchored at each batch's first
    spud in UTC. They do not slide forward with each additional well.
    """

    def detect_batches(
        self, bsee_df: pd.DataFrame, time_window_months: int = _LEGACY_MONTHS
    ) -> pd.DataFrame:
        """Return batches; warn on rejected/excluded rows. Prefer the report API."""
        result = self.detect_batches_with_report(bsee_df, time_window_months)
        self._warn_dispositions(result.reconciliation)
        return result.batches

    def detect_batches_with_report(
        self, bsee_df: pd.DataFrame, time_window_months: int = _LEGACY_MONTHS
    ) -> BatchDetectionResult:
        """Return batches and lossless row accounting without changing the input.

        Required identifiers are nonempty stripped strings. Dates are ISO text,
        date/datetime or Timestamp objects; naive dates assume UTC. Exact
        normalized duplicates are excluded, and conflicting valid events for
        one well identifier are all rejected. Missing or malformed rows are
        rejected before duplicate reconciliation. See the contract for reason
        precedence. Invalid schema/window arguments raise ValueError.
        """
        self._validate_columns(bsee_df, _REQUIRED_COLUMNS)
        if (
            isinstance(time_window_months, (bool, np.bool_))
            or not isinstance(time_window_months, Integral)
            or time_window_months <= 0
        ):
            raise ValueError("time_window_months must be a positive integer")
        records, dispositions = [], []
        for row_number, row in enumerate(bsee_df.to_dict("records")):
            normalized = {"row_number": row_number}
            reason = "accepted"
            for column in ("well_id", "rig_name", "field_name"):
                value = row[column]
                if _missing(value):
                    reason = f"missing_{column}"
                    break
                if not isinstance(value, str):
                    reason = f"invalid_{column}"
                    break
                normalized[column] = value.strip()
            if reason == "accepted":
                parsed, error = _parse_date(row["spud_date"])
                if error:
                    reason = f"{error}_spud_date"
                else:
                    normalized["spud_date"] = parsed
                    records.append(normalized)
            dispositions.append(
                [row_number, "accepted" if reason == "accepted" else "rejected", reason]
            )

        valid = pd.DataFrame(
            records,
            columns=["row_number", "well_id", "rig_name", "field_name", "spud_date"],
        )
        retained = []
        for _, events in valid.groupby("well_id", sort=False):
            unique = events.drop_duplicates(["rig_name", "field_name", "spud_date"])
            if len(unique) > 1:
                for number in events["row_number"]:
                    dispositions[number] = [number, "rejected", "conflicting_well_id"]
            else:
                retained.append(events.iloc[0].to_dict())
                for number in events["row_number"].iloc[1:]:
                    dispositions[number] = [number, "excluded", "duplicate_record"]

        batches = []
        if retained:
            valid = pd.DataFrame(retained).sort_values("spud_date", kind="stable")
            for (rig, field), group in valid.groupby(
                ["rig_name", "field_name"], sort=True
            ):
                group = group.reset_index(drop=True)
                start = 0
                while start < len(group):
                    first = group.loc[start, "spud_date"]
                    try:
                        end = first + pd.DateOffset(months=int(time_window_months))
                    except (ValueError, OverflowError) as exc:
                        raise ValueError(
                            "calendar window exceeds supported date range"
                        ) from exc
                    stop = start + 1
                    while stop < len(group) and group.loc[stop, "spud_date"] <= end:
                        stop += 1
                    members = group.iloc[start:stop]
                    last = members["spud_date"].iloc[-1]
                    batches.append(
                        {
                            "batch_id": f"BATCH-{len(batches) + 1:04d}",
                            "rig_name": rig,
                            "field_name": field,
                            "well_ids": members["well_id"].tolist(),
                            "batch_size": len(members),
                            "start_date": first,
                            "end_date": last,
                            # Unit conversion by a timedelta day, retaining sub-day spans.
                            "span_days": float((last - first) / pd.Timedelta(days=1)),
                        }
                    )
                    start = stop
        reconciliation = _reconciliation(dispositions)
        return BatchDetectionResult(
            pd.DataFrame(batches) if batches else self._empty_result(), reconciliation
        )

    def fit_learning_curve(self, campaign_df: pd.DataFrame) -> float:
        """Return a legacy scalar with warned fallback and inclusive clipping.

        Compatibility assumptions are 0.85 for insufficient/indistinct data
        and [0.5, 1.0] for clipping; neither is a calibrated acceptance limit.
        A numerically unrepresentable fit raises ValueError.
        """
        result = self.fit_learning_curve_with_report(
            campaign_df, default_factor=_LEGACY_DEFAULT, clip_bounds=_LEGACY_BOUNDS
        )
        self._warn_dispositions(result.reconciliation)
        if result.status != "FITTED":
            logger.warning("Learning fit %s: %s", result.status, result.reason)
        if result.factor is None:
            raise ValueError(f"Learning fit not evaluated: {result.reason}")
        return result.factor

    def fit_learning_curve_with_report(
        self,
        campaign_df: pd.DataFrame,
        *,
        default_factor: float | None = None,
        clip_bounds: tuple[float, float] | None = None,
    ) -> LearningFitResult:
        """Fit log(days) against log(position) with explicit optional policies.

        Positions must be finite positive integers; durations finite positive
        days. Decimal/scientific numeric text is allowed, locale punctuation,
        units, booleans and nonfinite values are rejected. Nonpositive pairs
        are excluded. Repeated positions remain equally weighted observations;
        at least two distinct positions are required. Without a caller default,
        insufficient data returns NOT_EVALUATED. No clipping is implicit.
        """
        self._validate_columns(campaign_df, _FIT_COLUMNS)
        if default_factor is not None and not _positive_policy(default_factor):
            raise ValueError("default_factor must be finite and positive")
        if clip_bounds is not None:
            if (
                not isinstance(clip_bounds, (tuple, list))
                or len(clip_bounds) != 2
                or not all(_positive_policy(bound) for bound in clip_bounds)
                or clip_bounds[0] > clip_bounds[1]
            ):
                raise ValueError("clip_bounds must be ordered finite positive values")
            if (
                default_factor is not None
                and not clip_bounds[0] <= default_factor <= clip_bounds[1]
            ):
                raise ValueError("default_factor must lie within clip_bounds")

        positions, times, dispositions = [], [], []
        for number, row in enumerate(campaign_df.to_dict("records")):
            values, status, reason = {}, "accepted", "accepted"
            for column in ("well_position", "days_to_drill"):
                value, error = _parse_number(row[column])
                if error:
                    status, reason = "rejected", f"{error}_{column}"
                    break
                if value <= 0:
                    status, reason = "excluded", f"nonpositive_{column}"
                    break
                if column == "well_position" and not value.is_integer():
                    status, reason = "rejected", "noninteger_well_position"
                    break
                values[column] = value
            dispositions.append([number, status, reason])
            if status == "accepted":
                positions.append(values["well_position"])
                times.append(values["days_to_drill"])
        reconciliation = _reconciliation(dispositions)
        reason = None
        # Two distinct observations identify the intercept and slope (NIST
        # e-Handbook, 2012, section 4.4.3.1, LS for Straight Line).
        if len(positions) < 2:
            reason = "insufficient_data"
        elif len(set(positions)) < 2:
            reason = "indistinct_positions"
        if reason:
            return LearningFitResult(
                float(default_factor) if default_factor is not None else None,
                None,
                None,
                "DEFAULTED" if default_factor is not None else "NOT_EVALUATED",
                reason,
                reconciliation,
            )
        x, y = np.log(positions), np.log(times)
        dx, dy = x - x.mean(), y - y.mean()
        # NIST/SEMATECH e-Handbook (2012), section 4.4.3.1: centered OLS slope.
        # LC=2**slope follows T(2N)/T(N)=2**slope for the defined power law;
        # 2 is the definition of doubling, not an empirical coefficient.
        with np.errstate(
            over="ignore", under="ignore", invalid="ignore", divide="ignore"
        ):
            slope = float(np.dot(dx, dy) / np.dot(dx, dx))
            raw = float(np.exp2(slope))
        if not np.isfinite(slope) or not np.isfinite(raw) or raw <= 0:
            return LearningFitResult(
                None, None, None, "NOT_EVALUATED", "nonfinite_fit", reconciliation
            )
        factor = (
            raw
            if clip_bounds is None
            else max(clip_bounds[0], min(raw, clip_bounds[1]))
        )
        clipped = factor != raw
        return LearningFitResult(
            float(factor),
            raw,
            slope,
            "CLIPPED" if clipped else "FITTED",
            "outside_clip_bounds" if clipped else "fit",
            reconciliation,
        )

    @staticmethod
    def _validate_columns(df: pd.DataFrame, required: set[str]) -> None:
        if not df.columns.is_unique:
            raise ValueError("input has duplicate column names")
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"input missing required columns: {sorted(missing)}")

    @staticmethod
    def _warn_dispositions(reconciliation: Reconciliation) -> None:
        counts = reconciliation.counts
        if counts["rejected"] or counts["excluded"]:
            logger.warning(
                "Input dispositions: accepted=%d rejected=%d excluded=%d; "
                "use the report API for row reasons",
                counts["accepted"],
                counts["rejected"],
                counts["excluded"],
            )

    @staticmethod
    def _empty_result() -> pd.DataFrame:
        return pd.DataFrame(
            columns=[
                "batch_id",
                "rig_name",
                "field_name",
                "well_ids",
                "batch_size",
                "start_date",
                "end_date",
                "span_days",
            ]
        )


def _reconciliation(dispositions: list[list]) -> Reconciliation:
    return Reconciliation(
        pd.DataFrame(dispositions, columns=["row_number", "status", "reason"])
    )


def _missing(value) -> bool:
    return (
        value is None
        or (isinstance(value, str) and not value.strip())
        or (pd.api.types.is_scalar(value) and bool(pd.isna(value)))
    )


def _parse_date(value) -> tuple[pd.Timestamp | None, str | None]:
    if _missing(value):
        return None, "missing"
    if isinstance(value, str):
        value = value.strip()
        if not _DATE.fullmatch(value):
            return None, "invalid"
    elif not isinstance(value, (date, datetime, pd.Timestamp, np.datetime64)):
        return None, "invalid"
    try:
        stamp = pd.Timestamp(value)
        stamp = (
            stamp.tz_localize("UTC")
            if stamp.tzinfo is None
            else stamp.tz_convert("UTC")
        )
        # Use one representable precision for grouping and elapsed-day arithmetic.
        return stamp.as_unit("ns"), None
    except (ValueError, TypeError, OverflowError):
        return None, "invalid"


def _parse_number(value) -> tuple[float | None, str | None]:
    if _missing(value):
        return None, "missing"
    if isinstance(value, str):
        value = value.strip()
        if not _NUMBER.fullmatch(value):
            return None, "invalid"
    elif isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        return None, "invalid"
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None, "invalid"
    return (number, None) if np.isfinite(number) else (None, "invalid")


def _positive_policy(value) -> bool:
    if not isinstance(value, Real) or isinstance(value, (bool, np.bool_)):
        return False
    number, error = _parse_number(value)
    return error is None and number > 0
