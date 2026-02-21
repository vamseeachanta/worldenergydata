"""
ABOUTME: Data-driven calibrator for well planning risk probabilities.
ABOUTME: Maps BSEE HSE incident frequencies to WellPlanningRisk.probability fields.
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from worldenergydata.well_planning.risk_model import WellPlanningRisk
from worldenergydata.well_planning.risk_registry import WELL_PLANNING_RISKS

# ---------------------------------------------------------------------------
# Mapping: (incident_type, sub_type) -> [risk_id, ...]
# ---------------------------------------------------------------------------

HSE_TO_RISK_MAP: dict[tuple[str, str], list[str]] = {
    # (incident_type, sub_type) -> [risk_id, ...]
    ("kick", "pressure_control"): ["OP-002", "OP-005"],    # narrow MW window, kick/loss
    ("stuck_pipe", "mechanical"): ["OP-001", "OP-003"],    # clay, stuck pipe
    ("lost_circulation", "formation"): ["OP-002", "OP-004"],  # narrow MW, hole cleaning
    ("bop_failure", "equipment"): ["TC-001"],               # casing design / ECD
    ("dropped_object", "crane"): ["TC-002"],                # rig trip speed / deck ops
    ("H2S", "gas"): ["OP-006"],                             # differential sticking / toxic gas
    ("well_control", "blowout"): ["OP-002", "TC-001"],
    ("casing_collapse", "wellbore"): ["TC-003"],            # wellhead pressure rating
    ("rig_move", "marine"): ["ST-001"],                     # rig MPD capability / weather
    ("regulatory", "compliance"): ["ST-002"],               # permit / compliance
}

MIN_INCIDENTS_FOR_CALIBRATION = 5  # lower than ENIGMA since well events are rarer

_SEVERITY_WEIGHTS: dict[str, float] = {
    "fatality": 2.0,
    "lost_time": 1.5,
    "recordable": 1.0,
    "near_miss": 0.5,
    "minor": 0.3,
}

# Normalization factor: events_per_year -> data_probability domain
# Chosen so that ~3 events/yr maps to probability ~0.60
NORMALIZATION_FACTOR: float = 5.0

_INCIDENT_TYPES = list(HSE_TO_RISK_MAP.keys())


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CalibrationRecord:
    """Calibration outcome for a single risk_id."""

    risk_id: str
    category: str
    events_per_year: float
    calibrated_probability: float
    baseline_probability: float
    confidence: str        # "high" / "medium" / "low"
    data_driven: bool


@dataclass
class RiskCalibrationReport:
    """Aggregate report produced by :class:`RiskCalibrator`."""

    total_incidents_used: int
    years_covered: float
    records: list[CalibrationRecord] = field(default_factory=list)
    coverage_pct: float = 0.0

    def to_dataframe(self) -> pd.DataFrame:
        """Return DataFrame with one row per CalibrationRecord."""
        rows = [
            {
                "risk_id": r.risk_id,
                "category": r.category,
                "events_per_year": r.events_per_year,
                "calibrated_probability": r.calibrated_probability,
                "baseline_probability": r.baseline_probability,
                "confidence": r.confidence,
                "data_driven": r.data_driven,
            }
            for r in self.records
        ]
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Calibrator
# ---------------------------------------------------------------------------


class RiskCalibrator:
    """Calibrate WellPlanningRisk probabilities from BSEE HSE incident data.

    Usage::

        df = RiskCalibrator.synthetic_hse_dataframe()
        calibrator = RiskCalibrator()
        calibrator.calibrate(df)
        report = calibrator.calibration_report()
        prob, is_data_driven = calibrator.risk_probability("OP-002")
        updated_risks = calibrator.calibrate_registry()
    """

    def __init__(self) -> None:
        self._prob_map: dict[str, float] = {}
        self._data_driven_ids: set[str] = set()
        self._report: Optional[RiskCalibrationReport] = None
        self._fitted = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calibrate(self, hse_df: pd.DataFrame) -> "RiskCalibrator":
        """Map BSEE HSE incidents to WellPlanningRisk probabilities.

        Expected columns: date (or year), incident_type, sub_type, severity.
        Severity weights: fatality=2.0, lost_time=1.5, recordable=1.0,
        near_miss=0.5, minor=0.3.

        For each risk_id with >= MIN_INCIDENTS_FOR_CALIBRATION:
          - events_per_year = weighted_count / years_covered
          - data_probability = min(0.95, max(0.05, events_per_year / NORMALIZATION_FACTOR))
          - calibrated_probability = 0.6 * data_probability + 0.4 * baseline_probability

        Falls back to baseline probability for sparse combos.

        Returns self for chaining.
        """
        if not hse_df.empty:
            _required = {"incident_type", "sub_type"}
            missing = _required - set(hse_df.columns)
            if missing:
                raise ValueError(
                    f"hse_df is missing required columns: {sorted(missing)}"
                )

        years_covered = self._parse_years_covered(hse_df)

        # Weighted count per risk_id
        risk_weighted: dict[str, float] = {}
        risk_raw: dict[str, int] = {}
        total_mapped = 0

        if not hse_df.empty:
            for _, row in hse_df.iterrows():
                risk_ids = self._map_row_to_risks(row)
                if not risk_ids:
                    continue
                severity = str(row.get("severity", "recordable")).lower()
                weight = _SEVERITY_WEIGHTS.get(severity, 1.0)
                for rid in risk_ids:
                    risk_weighted[rid] = risk_weighted.get(rid, 0.0) + weight
                    risk_raw[rid] = risk_raw.get(rid, 0) + 1
                    total_mapped += 1

        # Build calibrated probabilities per risk
        self._prob_map = {}
        self._data_driven_ids = set()

        baseline_map = {r.risk_id: r.probability for r in WELL_PLANNING_RISKS}

        records: list[CalibrationRecord] = []

        for risk in WELL_PLANNING_RISKS:
            rid = risk.risk_id
            baseline = baseline_map.get(rid, 0.5)
            raw_count = risk_raw.get(rid, 0)
            weighted_count = risk_weighted.get(rid, 0.0)
            events_per_year = weighted_count / years_covered if years_covered > 0 else 0.0

            if raw_count >= MIN_INCIDENTS_FOR_CALIBRATION:
                data_prob = float(np.clip(
                    events_per_year / NORMALIZATION_FACTOR, 0.05, 0.95
                ))
                calibrated = float(np.clip(
                    0.6 * data_prob + 0.4 * baseline, 0.05, 0.95
                ))
                data_driven = True
                if raw_count >= 20:
                    confidence = "high"
                elif raw_count >= MIN_INCIDENTS_FOR_CALIBRATION:
                    confidence = "medium"
                else:
                    confidence = "low"
                self._data_driven_ids.add(rid)
            else:
                calibrated = baseline
                data_driven = False
                confidence = "low"

            self._prob_map[rid] = calibrated

            records.append(
                CalibrationRecord(
                    risk_id=rid,
                    category=risk.category.value,
                    events_per_year=round(events_per_year, 4),
                    calibrated_probability=round(calibrated, 4),
                    baseline_probability=round(baseline, 4),
                    confidence=confidence,
                    data_driven=data_driven,
                )
            )

        n_risks = len(WELL_PLANNING_RISKS)
        data_driven_count = len(self._data_driven_ids)
        coverage_pct = (data_driven_count / n_risks * 100.0) if n_risks > 0 else 0.0

        self._report = RiskCalibrationReport(
            total_incidents_used=total_mapped,
            years_covered=years_covered,
            records=records,
            coverage_pct=round(coverage_pct, 2),
        )
        self._fitted = True
        return self

    def calibration_report(self) -> RiskCalibrationReport:
        """Return calibration report. Raises RuntimeError if calibrate() not called."""
        if not self._fitted:
            raise RuntimeError(
                "RiskCalibrator.calibrate() must be called before calibration_report()."
            )
        return self._report  # type: ignore[return-value]

    def calibrate_registry(self) -> list[WellPlanningRisk]:
        """Return copy of WELL_PLANNING_RISKS with updated probability fields.

        Raises RuntimeError if calibrate() has not been called.
        """
        if not self._fitted:
            raise RuntimeError(
                "RiskCalibrator.calibrate() must be called before calibrate_registry()."
            )
        updated: list[WellPlanningRisk] = []
        for risk in WELL_PLANNING_RISKS:
            new_prob = self._prob_map.get(risk.risk_id, risk.probability)
            cloned = copy.copy(risk)
            object.__setattr__(cloned, "probability", round(new_prob, 4))
            object.__setattr__(
                cloned, "risk_score", round(cloned.severity.value * new_prob, 4)
            )
            updated.append(cloned)
        return updated

    def risk_probability(self, risk_id: str) -> tuple[float, bool]:
        """Return (probability, is_data_driven) for a given risk_id.

        Falls back to baseline probability if calibrate() was not called.
        """
        baseline_map = {r.risk_id: r.probability for r in WELL_PLANNING_RISKS}
        if not self._fitted:
            baseline = baseline_map.get(risk_id, 0.5)
            return baseline, False
        prob = self._prob_map.get(
            risk_id, baseline_map.get(risk_id, 0.5)
        )
        is_data_driven = risk_id in self._data_driven_ids
        return prob, is_data_driven

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def synthetic_hse_dataframe(n_incidents: int = 150) -> pd.DataFrame:
        """Self-contained GoM-pattern BSEE HSE incidents.

        Uses seeded rng(42) for reproducibility.
        """
        rng = np.random.default_rng(42)

        incident_keys = list(HSE_TO_RISK_MAP.keys())
        incident_types = [k[0] for k in incident_keys]
        sub_types = [k[1] for k in incident_keys]
        n_types = len(incident_keys)

        # Weights favour well-control and stuck_pipe events (GoM pattern)
        weights = np.array([
            0.12,   # kick / pressure_control
            0.14,   # stuck_pipe / mechanical
            0.10,   # lost_circulation / formation
            0.08,   # bop_failure / equipment
            0.08,   # dropped_object / crane
            0.07,   # H2S / gas
            0.12,   # well_control / blowout
            0.09,   # casing_collapse / wellbore
            0.10,   # rig_move / marine
            0.10,   # regulatory / compliance
        ], dtype=float)
        weights = weights / weights.sum()

        assert len(weights) == n_types, "Weight count must match incident key count"

        chosen_indices = rng.choice(n_types, size=n_incidents, p=weights)
        chosen_incident_types = [incident_types[i] for i in chosen_indices]
        chosen_sub_types = [sub_types[i] for i in chosen_indices]

        severities = ["fatality", "lost_time", "recordable", "near_miss", "minor"]
        severity_weights = [0.03, 0.12, 0.40, 0.28, 0.17]
        chosen_severities = rng.choice(
            severities, size=n_incidents, p=severity_weights
        )

        # Date range: 2014-01-01 to 2023-12-31 (~10 years)
        start_ts = pd.Timestamp("2014-01-01")
        end_ts = pd.Timestamp("2023-12-31")
        date_range_days = (end_ts - start_ts).days
        random_days = rng.integers(0, date_range_days, size=n_incidents)
        incident_dates = [
            start_ts + pd.Timedelta(days=int(d)) for d in random_days
        ]

        operators = ["Shell", "BP", "Chevron", "ExxonMobil", "ConocoPhillips"]

        return pd.DataFrame(
            {
                "incident_type": chosen_incident_types,
                "sub_type": chosen_sub_types,
                "severity": chosen_severities,
                "date": incident_dates,
                "operator": rng.choice(operators, size=n_incidents).tolist(),
                "well_id": [
                    f"GOM-{rng.integers(1000, 9999)}" for _ in range(n_incidents)
                ],
            }
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _map_row_to_risks(self, row: pd.Series) -> list[str]:
        """Map a single incident row to a list of risk_ids."""
        inc_type = str(row.get("incident_type", "")).strip()
        sub_type = str(row.get("sub_type", "")).strip()
        key = (inc_type, sub_type)
        return list(HSE_TO_RISK_MAP.get(key, []))

    def _parse_years_covered(self, hse_df: pd.DataFrame) -> float:
        """Derive years covered from a date or year column; fallback to 1.0."""
        if hse_df.empty:
            return 1.0

        for col in ("date", "year", "incident_date"):
            if col not in hse_df.columns:
                continue
            try:
                series = hse_df[col]
                if col == "year":
                    numeric = pd.to_numeric(series, errors="coerce").dropna()
                    if numeric.empty:
                        continue
                    years = float(numeric.max() - numeric.min())
                    return max(years, 1.0)
                else:
                    dates = pd.to_datetime(series, errors="coerce").dropna()
                    if dates.empty:
                        continue
                    years = (dates.max() - dates.min()).days / 365.25
                    return max(years, 1.0)
            except Exception:
                continue

        return 1.0
