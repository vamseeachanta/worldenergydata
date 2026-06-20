"""Empirical well-access / intervention-rate calibration from BSEE history (#510).

Derives *measured* calibration parameters for the well-access / intervention
lifecycle engine (which lives in digitalmodel ``well_access/``, digitalmodel#849)
from real BSEE Well Activity Report (WAR) history, rather than from assumptions:

- per intervention type (workover ``WO`` / recompletion ``REC`` / sidetrack ``ST``)
  empirical event counts and durations;
- intervention frequency (events per well-exposure-year) where exposure can be
  grounded;
- ``A_facility`` uptime / utilization from production ``DAYS_ON_PROD`` when present.

Design principles (issue #510):

- **Reuse, don't rebuild.** The WAR activity-code taxonomy and the rig-day
  duration convention are taken from the existing
  ``worldenergydata.lower_tertiary.ops_timeline`` (``INTERVENTION_CODES``,
  ``WAR_ACTIVITY_LABELS``) and ``bsee.analysis.well_rig_days.WellRigDays``
  (rig_days = ``(WAR_END_DT - WAR_START_DT).days + 1``).
- **Hard data-vs-assumption separation.** Every emitted parameter carries a
  ``source`` of either ``"measured"`` (grounded in the local subset, with a
  ``sample_size``) or ``"needs_full_dataset"`` (structure only — *no fabricated
  rate*). Low-confidence measured values are flagged.
- **Deterministic + network-free.** Pure functions over already-local files.

Import-light: this package pulls only stdlib + pandas + (lazily) the resolver.
The resolver is loaded by file path if the heavy ``common`` ``__init__`` blocks
the normal import (#407/#451/#418).

Example::

    from worldenergydata.bsee.analysis import well_access_calibration as wac
    cal = wac.calibrate()            # from the local BSEE subset
    wac.write_calibration_yaml(cal, "calibration.yml")
"""

from __future__ import annotations

from .calibrator import (
    INTERVENTION_TYPES,
    CalibrationResult,
    ParamSource,
    calibrate,
    calibrate_from_frames,
    write_calibration_yaml,
)

__all__ = [
    "INTERVENTION_TYPES",
    "CalibrationResult",
    "ParamSource",
    "calibrate",
    "calibrate_from_frames",
    "write_calibration_yaml",
]
