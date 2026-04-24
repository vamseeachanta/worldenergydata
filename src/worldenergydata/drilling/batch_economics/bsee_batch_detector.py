# ABOUTME: BSEE historical batch campaign detector for WRK-219.
# ABOUTME: Heuristic: same rig + same field/block within time window = batch.

"""BSEE historical batch campaign detector.

Identifies batch drilling campaigns from BSEE activity data using a heuristic
grouping rule: same rig, same field/block, wells spud within a rolling time
window.

Also provides a learning curve fitting utility for historical batch sequences.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

_REQUIRED_COLUMNS = {"well_id", "rig_name", "field_name", "spud_date"}


class BSEEBatchDetector:
    """Detect historical batch drilling campaigns from BSEE activity data.

    The core heuristic:
        A batch is a group of wells drilled by the same rig in the same
        field/block where all spud dates fall within a rolling
        ``time_window_months`` window.
    """

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_batches(
        self,
        bsee_df: pd.DataFrame,
        time_window_months: int = 12,
    ) -> pd.DataFrame:
        """Detect batch campaigns from BSEE-style drilling activity data.

        Groups wells by (rig_name, field_name) and assigns them to rolling
        time windows.  Any group of >=1 well(s) sharing the same rig and
        field within the window becomes a batch record.

        Args:
            bsee_df: DataFrame with at minimum columns:
                well_id, rig_name, field_name, spud_date.
            time_window_months: Maximum span (in months) between first and
                last spud date within a single batch.

        Returns:
            DataFrame of detected batches with columns:
                batch_id, rig_name, field_name, well_ids (list), batch_size,
                start_date, end_date, span_days.
            Returns empty DataFrame if no valid data is found.
        """
        self._validate_columns(bsee_df)

        if bsee_df.empty:
            return self._empty_result()

        df = bsee_df.copy()
        df["spud_date"] = pd.to_datetime(df["spud_date"])
        df = df.sort_values("spud_date").reset_index(drop=True)

        window_days = time_window_months * 30.44  # approximate

        batches: list[dict] = []
        batch_counter = 0

        for (rig, field), group in df.groupby(["rig_name", "field_name"]):
            group = group.sort_values("spud_date").reset_index(drop=True)
            assigned = [False] * len(group)

            i = 0
            while i < len(group):
                if assigned[i]:
                    i += 1
                    continue

                window_start = group.loc[i, "spud_date"]
                window_end = window_start + pd.Timedelta(days=window_days)

                # Collect all wells within the rolling window
                members = []
                for j in range(i, len(group)):
                    if group.loc[j, "spud_date"] <= window_end:
                        members.append(j)
                        assigned[j] = True
                    else:
                        break  # sorted, so no further wells fit this window

                if members:
                    batch_counter += 1
                    member_rows = group.loc[members]
                    start_dt = member_rows["spud_date"].min()
                    end_dt = member_rows["spud_date"].max()
                    batches.append(
                        {
                            "batch_id": f"BATCH-{batch_counter:04d}",
                            "rig_name": rig,
                            "field_name": field,
                            "well_ids": member_rows["well_id"].tolist(),
                            "batch_size": len(members),
                            "start_date": start_dt,
                            "end_date": end_dt,
                            "span_days": (end_dt - start_dt).days,
                        }
                    )

                i = max(i + 1, (members[-1] + 1) if members else i + 1)

        if not batches:
            return self._empty_result()

        return pd.DataFrame(batches)

    def fit_learning_curve(self, campaign_df: pd.DataFrame) -> float:
        """Fit a Wright learning curve factor to historical batch well data.

        Expects a DataFrame with columns:
            well_position (int, 1-based), days_to_drill (float).

        Fits: log(T) = log(T1) + b * log(N)
        where b = log(LC) / log(2), so LC = 2^b.

        Args:
            campaign_df: DataFrame with well_position and days_to_drill.

        Returns:
            Fitted learning curve factor LC in (0.5, 1.0].
            Falls back to 0.85 on insufficient data.
        """
        if campaign_df.empty or len(campaign_df) < 2:
            logger.warning("Insufficient data for LC fit; returning default 0.85")
            return 0.85

        positions = campaign_df["well_position"].astype(float).values
        times = campaign_df["days_to_drill"].astype(float).values

        # Filter out non-positive values
        mask = (positions > 0) & (times > 0)
        if mask.sum() < 2:
            return 0.85

        log_n = np.log(positions[mask])
        log_t = np.log(times[mask])

        # Least-squares fit: log_t = intercept + slope * log_n
        slope, _ = np.polyfit(log_n, log_t, 1)

        # Convert slope b back to LC factor: LC = 2^b
        lc = float(2.0**slope)

        # Clip to a sensible range for drilling learning curves
        lc = max(0.5, min(lc, 1.0))
        return lc

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_columns(self, df: pd.DataFrame) -> None:
        """Raise ValueError if required columns are missing."""
        missing = _REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"bsee_df missing required columns: {sorted(missing)}")

    @staticmethod
    def _empty_result() -> pd.DataFrame:
        """Return an empty DataFrame with the standard batch schema."""
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
