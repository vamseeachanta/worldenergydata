# ABOUTME: Historical batch detection with explicit per-row reconciliation.
# ABOUTME: Calendar-window grouping and auditable log-space learning fits.

"""Heuristic activity grouping and learning fits, with auditable dispositions.

See ``docs/detector-contracts.md`` beside the package documentation for the
parsing policy, equations, legacy policy limits and a worked example.
"""

from __future__ import annotations

import logging
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from numbers import Integral

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {"well_id", "rig_name", "field_name", "spud_date"}
_RECORD_COLUMNS = ["row_position", "source_index", "disposition", "reason"]
# Decimal/scientific notation only; no thousands separators, units or Booleans.
_NUMERIC_TEXT = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z"
)
# Legacy application policy, NOT engineering limits: agent-pack.md revision 2,
# section 2, 'Learning DataFrame' and 'Fitted factor'. Calibration is unqualified.
_DEFAULT_FACTOR = 0.85
_FACTOR_BOUNDS = (0.5, 1.0)


@dataclass
class DetectionResult:
    """Batch table plus exactly one disposition per input row."""

    batches: pd.DataFrame
    records: pd.DataFrame

    @property
    def counts(self) -> dict[str, int]:
        return _counts(self.records)


@dataclass
class LearningFitResult:
    """A fit/default, its unclipped factor, and the retained row evidence.

    ``qualification`` concerns engineering applicability; a successful numerical
    fit alone cannot establish that applicability or qualify the legacy bounds.
    """

    factor: float
    raw_factor: float | None
    status: str
    reason: str
    records: pd.DataFrame
    qualification: str = "NOT_EVALUATED"

    @property
    def counts(self) -> dict[str, int]:
        return _counts(self.records)


def _counts(records: pd.DataFrame) -> dict[str, int]:
    counts = records["disposition"].value_counts()
    return {
        name: int(counts.get(name, 0)) for name in ("accepted", "rejected", "excluded")
    }


def _require_columns(df: pd.DataFrame, required: set[str]) -> None:
    if not df.columns.is_unique:
        raise ValueError("input columns must be unique")
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"input missing required columns: {sorted(missing)}")


def _record(position: int, index: object, disposition: str, reason: str) -> dict:
    return dict(
        row_position=position,
        source_index=index,
        disposition=disposition,
        reason=reason,
    )


def _parse_date(value: object) -> pd.Timestamp:
    # pandas to_datetime reference (2026), format and utc sections:
    # https://pandas.pydata.org/docs/reference/api/pandas.to_datetime.html
    # Naive dates are explicitly UTC; numeric epochs have no declared units.
    if isinstance(value, str):
        if not re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}(?:[Tt ]|$)", value.strip()):
            return pd.NaT
        return pd.to_datetime(
            value.strip(), format="ISO8601", utc=True, errors="coerce"
        )
    if isinstance(value, (date, datetime, pd.Timestamp, np.datetime64)):
        return pd.to_datetime(value, utc=True, errors="coerce")
    return pd.NaT


def _parse_number(value: object, column: str) -> tuple[float | None, str | None]:
    if value is None or value is pd.NA or value is pd.NaT:
        return None, f"missing_{column}"
    if isinstance(value, (bool, np.bool_)):
        return None, f"invalid_{column}"
    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None, f"missing_{column}"
        if not _NUMERIC_TEXT.fullmatch(value):
            return None, f"invalid_{column}"
    elif not isinstance(value, (int, float, np.integer, np.floating)):
        return None, f"invalid_{column}"
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        return None, f"invalid_{column}"
    if math.isnan(number):
        return None, f"missing_{column}"
    if not math.isfinite(number):
        return None, f"nonfinite_{column}"
    if number <= 0:
        return None, f"nonpositive_{column}"
    if column == "well_position" and not number.is_integer():
        return None, "noninteger_well_position"
    return number, None


class BSEEBatchDetector:
    """Group accepted event rows by rig, field and an anchored calendar window.

    Existing DataFrame/scalar entry points remain available. The diagnostic
    entry points expose dispositions without storing mutable state on this class.
    """

    def detect_batches(
        self, bsee_df: pd.DataFrame, time_window_months: int = 12
    ) -> pd.DataFrame:
        """Return batches; warn when any input row is rejected or excluded.

        The default window is legacy application policy (agent-pack revision 2,
        section 2), not a physically qualified campaign-separation criterion.
        """
        result = self.detect_batches_with_diagnostics(bsee_df, time_window_months)
        if result.counts["rejected"] or result.counts["excluded"]:
            logger.warning("Batch detection dispositions: %s", result.counts)
        return result.batches

    def detect_batches_with_diagnostics(
        self, bsee_df: pd.DataFrame, time_window_months: int = 12
    ) -> DetectionResult:
        """Reconcile all rows, then group inclusive windows from the first row.

        Keys must be nonblank strings; integral numeric well IDs become text.
        Exact normalized required-column
        duplicates are excluded after their first valid occurrence. Distinct
        events for a repeated well remain accepted; batch_size counts events.
        """
        _require_columns(bsee_df, _REQUIRED_COLUMNS)
        if (
            isinstance(time_window_months, (bool, np.bool_))
            or not isinstance(time_window_months, Integral)
            or time_window_months <= 0
        ):
            raise ValueError("time_window_months must be a positive integer")
        accepted, records, seen = [], [], set()
        for position, (index, row) in enumerate(bsee_df.iterrows()):
            normalized, reasons = {}, []
            for key in ("well_id", "rig_name", "field_name"):
                value = row[key]
                if key == "well_id" and not isinstance(value, (bool, np.bool_)):
                    if isinstance(value, Integral):
                        value = str(int(value))
                    elif (
                        isinstance(value, (float, np.floating))
                        and np.isfinite(value)
                        and value == np.floor(value)
                    ):
                        value = str(int(value))
                if isinstance(value, str) and value.strip():
                    normalized[key] = value.strip()
                else:
                    missing = (
                        value is None
                        or value is pd.NA
                        or (isinstance(value, str) and not value.strip())
                        or (isinstance(value, float) and math.isnan(value))
                    )
                    reasons.append(f"{'missing' if missing else 'invalid'}_{key}")
            parsed = _parse_date(row["spud_date"])
            if pd.isna(parsed):
                reasons.append("invalid_spud_date")
            if reasons:
                records.append(_record(position, index, "rejected", ";".join(reasons)))
                continue
            normalized["spud_date"] = parsed
            identity = tuple(normalized[key] for key in sorted(_REQUIRED_COLUMNS))
            if identity in seen:
                records.append(_record(position, index, "excluded", "duplicate_record"))
                continue
            seen.add(identity)
            accepted.append(normalized)
            records.append(_record(position, index, "accepted", "accepted"))
        batches = self._group(accepted, int(time_window_months))
        return DetectionResult(batches, pd.DataFrame(records, columns=_RECORD_COLUMNS))

    @staticmethod
    def _group(accepted: list[dict], months: int) -> pd.DataFrame:
        batches = []
        if not accepted:
            return BSEEBatchDetector._empty_result()
        df = pd.DataFrame(accepted)
        for (rig, field), group in df.groupby(["rig_name", "field_name"], sort=True):
            group = group.sort_values("spud_date", kind="stable").reset_index(drop=True)
            start = 0
            while start < len(group):
                first = group.iloc[start].spud_date
                # Calendar offset (inclusive), not an approximate days/month:
                # pandas DateOffset reference (2026), months keyword.
                end = first + pd.DateOffset(months=months)
                stop = start + 1
                while stop < len(group) and group.iloc[stop].spud_date <= end:
                    stop += 1
                rows = group.iloc[start:stop]
                last = rows.iloc[-1].spud_date
                batches.append(
                    dict(
                        batch_id=f"BATCH-{len(batches) + 1:04d}",
                        rig_name=rig,
                        field_name=field,
                        well_ids=rows.well_id.tolist(),
                        batch_size=len(rows),
                        start_date=first,
                        end_date=last,
                        # A day is a Timedelta unit; retain sub-day elapsed time.
                        span_days=float((last - first) / pd.Timedelta(days=1)),
                    )
                )
                start = stop
        return pd.DataFrame(batches)

    def fit_learning_curve(self, campaign_df: pd.DataFrame) -> float:
        """Return legacy bounded factor; warn about filtering/default/clipping."""
        result = self.fit_learning_curve_with_diagnostics(campaign_df)
        if result.status != "fitted" or result.counts["rejected"]:
            logger.warning(
                "Learning fit %s (%s): %s", result.status, result.reason, result.counts
            )
        return result.factor

    def fit_learning_curve_with_diagnostics(
        self, campaign_df: pd.DataFrame
    ) -> LearningFitResult:
        """Fit log(T)=a+b*log(N); factor=T(2N)/T(N)=2**b.

        N is a positive integer position; T is a positive finite duration in
        elapsed days. Numeric text accepts decimal/scientific notation only.
        Replicated positions remain observations; at least two distinct usable
        positions are needed to identify the intercept and slope.
        """
        _require_columns(campaign_df, {"well_position", "days_to_drill"})
        positions, times, records = [], [], []
        for position, (index, row) in enumerate(campaign_df.iterrows()):
            number, n_reason = _parse_number(row["well_position"], "well_position")
            duration, t_reason = _parse_number(row["days_to_drill"], "days_to_drill")
            reasons = [reason for reason in (n_reason, t_reason) if reason]
            if reasons:
                records.append(_record(position, index, "rejected", ";".join(reasons)))
            else:
                positions.append(number)
                times.append(duration)
                records.append(_record(position, index, "accepted", "accepted"))
        evidence = pd.DataFrame(records, columns=_RECORD_COLUMNS)
        if len(positions) < 2:
            return LearningFitResult(
                _DEFAULT_FACTOR, None, "defaulted", "insufficient_data", evidence
            )
        if len(set(positions)) < 2:
            return LearningFitResult(
                _DEFAULT_FACTOR, None, "defaulted", "constant_position", evidence
            )
        # Centered scalar least squares, equivalent to the linear system in
        # NumPy lstsq reference (2026), Notes/Examples. Two distinct x values
        # identify two coefficients; no empirical acceptance tolerance is used.
        x, y = np.log(positions), np.log(times)
        centered_x, centered_y = x - x.mean(), y - y.mean()
        denominator = float(centered_x @ centered_x)
        if denominator == 0:
            return LearningFitResult(
                _DEFAULT_FACTOR, None, "defaulted", "constant_position", evidence
            )
        slope = float(centered_x @ centered_y) / denominator
        # Algebraic doubling ratio of the stated power law, not a coefficient
        # imported from a drilling calibration. exp2 may overflow; expose that.
        with np.errstate(over="ignore", under="ignore"):
            raw = float(np.exp2(slope))
        lower, upper = _FACTOR_BOUNDS
        # Numerical endpoint guard only, scaled by log magnitude and row count.
        # NumPy finfo.eps defines float spacing at unity, not an engineering
        # acceptance limit. Preserve the unrounded raw factor in the result.
        roundoff = np.finfo(float).eps * len(x) * max(1, abs(x).max(), abs(y).max())
        at_boundary = any(
            math.isclose(raw, bound, rel_tol=roundoff, abs_tol=0)
            for bound in (lower, upper)
        )
        status = (
            "fitted"
            if at_boundary
            else (
                "clipped_lower"
                if raw < lower
                else "clipped_upper" if raw > upper else "fitted"
            )
        )
        factor = max(lower, min(raw, upper))
        return LearningFitResult(
            factor, raw, status, "log_space_least_squares", evidence
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
