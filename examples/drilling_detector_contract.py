"""Synthetic worked detector example; see drilling/docs/detector-contract.md.

Hand oracle: Jan 31 + one month = Feb 29 in the chosen leap year; span=29 days.
The accepted durations halve with each doubling of position, so slope=-1 and
LC=0.5. Bounds are synthetic caller policy, not calibrated drilling limits.
"""

import json

import pandas as pd

from worldenergydata.drilling import BSEEBatchDetector


def worked_example() -> dict:
    activity = pd.DataFrame(
        {
            "well_id": ["well-a", "well-b", "well-c", "well-a"],
            "rig_name": ["rig", "rig", None, "rig"],
            "field_name": ["field"] * 4,
            "spud_date": ["2024-01-31", "2024-02-29", "2024-02-01", "2024-01-31"],
        }
    )
    durations = pd.DataFrame(
        {
            "well_position": [1, 2, 4, 0],
            "days_to_drill": [8, 4, 2, 8],
        }
    )
    detector = BSEEBatchDetector()
    batches = detector.detect_batches_with_report(activity, time_window_months=1)
    fitted = detector.fit_learning_curve_with_report(durations, clip_bounds=(0.5, 1.0))
    return {
        "activity_input": activity.to_dict("records"),
        "duration_input": durations.to_dict("records"),
        "batch_sizes": batches.batches["batch_size"].tolist(),
        "spans_days": batches.batches["span_days"].tolist(),
        "activity_counts": batches.reconciliation.counts,
        "activity_dispositions": batches.reconciliation.rows.to_dict("records"),
        "fit_counts": fitted.reconciliation.counts,
        "fit_dispositions": fitted.reconciliation.rows.to_dict("records"),
        "slope": fitted.slope,
        "factor": fitted.factor,
        "fit_status": fitted.status,
    }


if __name__ == "__main__":
    print(json.dumps(worked_example(), indent=2))
