"""
ABOUTME: Data-driven ENIGMA risk score calibrator using real BSEE HSE incident data.
ABOUTME: EnigmaCalibrator.fit(hse_df) -> calibrated risk matrix from incident frequencies.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from worldenergydata.safety_analysis.skill import (
    _ASSET_MODIFIER,
    _SCENARIO_BASE,
    _VALID_ASSET_TYPES,
    _VALID_SCENARIOS,
    _risk_level_from_score,
)

# ---------------------------------------------------------------------------
# Mapping: (incident_type, sub_key) -> [(asset_type, scenario), ...]
# ---------------------------------------------------------------------------

HSE_TO_ENIGMA_MAP: dict[tuple[str, str], list[tuple[str, str]]] = {
    # equipment_failure rows keyed on lowercase equipment_type
    ("equipment_failure", "bop"): [
        ("wellhead", "overpressure"),
        ("riser", "overpressure"),
    ],
    ("equipment_failure", "crane"): [
        ("platform", "dropped_object"),
        ("vessel", "dropped_object"),
    ],
    ("equipment_failure", "fire_detection"): [
        ("platform", "fire_explosion"),
        ("vessel", "fire_explosion"),
    ],
    ("equipment_failure", "hipps"): [
        ("wellhead", "overpressure"),
        ("platform", "overpressure"),
    ],
    ("equipment_failure", "safety_valve"): [
        ("riser", "overpressure"),
        ("wellhead", "overpressure"),
    ],
    # spill rows keyed on lowercase spill_location keywords
    ("spill", "pipeline"): [
        ("subsea_pipeline", "corrosion"),
        ("subsea_pipeline", "structural"),
    ],
    ("spill", "platform"): [
        ("platform", "corrosion"),
        ("platform", "structural"),
    ],
    # injury rows keyed on lowercase injury_type keywords
    ("injury", "fire"): [
        ("platform", "fire_explosion"),
        ("vessel", "fire_explosion"),
    ],
    ("injury", "structural"): [
        ("platform", "structural"),
        ("vessel", "structural"),
    ],
    ("injury", "dropped_object"): [
        ("platform", "dropped_object"),
        ("vessel", "dropped_object"),
    ],
}

MIN_INCIDENTS_FOR_CALIBRATION = 10

_SEVERITY_WEIGHTS: dict[str, float] = {
    "fatality": 2.0,
    "lost_time": 1.5,
    "recordable": 1.0,
    "near_miss": 0.5,
    "minor": 0.3,
}

_VALID_INCIDENT_TYPES = {"equipment_failure", "spill", "injury", "violation"}


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CalibrationRecord:
    asset_type: str
    scenario: str
    incident_count: int
    incidents_per_year: float
    calibrated_score: float
    confidence: str  # "high" (>=50), "medium" (10-49), "low" (<10 rule-based)
    data_driven: bool


@dataclass
class CalibrationReport:
    total_incidents_used: int
    date_range: tuple[str, str]
    years_covered: float
    records: list[CalibrationRecord] = field(default_factory=list)
    coverage_pct: float = 0.0

    def to_dataframe(self) -> pd.DataFrame:
        """Return DataFrame with calibration record fields."""
        rows = [
            {
                "asset_type": r.asset_type,
                "scenario": r.scenario,
                "incident_count": r.incident_count,
                "incidents_per_year": r.incidents_per_year,
                "calibrated_score": r.calibrated_score,
                "confidence": r.confidence,
                "data_driven": r.data_driven,
            }
            for r in self.records
        ]
        return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Calibrator
# ---------------------------------------------------------------------------


class EnigmaCalibrator:
    """
    Calibrates ENIGMA risk scores from real BSEE HSE incident data.

    Usage::

        df = EnigmaCalibrator.synthetic_hse_dataframe()
        calibrator = EnigmaCalibrator()
        calibrator.fit(df)
        report = calibrator.calibration_report()
        result = calibrator.assess("riser", "corrosion")
    """

    def __init__(self) -> None:
        self._calibrated_matrix: dict[tuple[str, str], float] = {}
        self._report: Optional[CalibrationReport] = None
        self._fitted = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def fit(self, hse_df: pd.DataFrame) -> "EnigmaCalibrator":
        """Fit calibration from HSE incident DataFrame."""
        if hse_df.empty:
            self._fitted = True
            self._report = CalibrationReport(
                total_incidents_used=0,
                date_range=("", ""),
                years_covered=0.0,
                records=self._build_fallback_records({}),
                coverage_pct=0.0,
            )
            return self

        years_covered, date_range = self._parse_date_range(hse_df)
        years_covered = max(years_covered, 1.0)

        # Count weighted incidents per (asset_type, scenario)
        combo_counts: dict[tuple[str, str], float] = {}
        combo_raw_counts: dict[tuple[str, str], int] = {}
        total_mapped = 0

        for _, row in hse_df.iterrows():
            combos = self._map_row_to_enigma(row)
            if not combos:
                continue
            severity = str(row.get("severity", "recordable")).lower()
            weight = _SEVERITY_WEIGHTS.get(severity, 1.0)
            for combo in combos:
                combo_counts[combo] = combo_counts.get(combo, 0.0) + weight
                combo_raw_counts[combo] = combo_raw_counts.get(combo, 0) + 1
                total_mapped += 1

        # Compute incidents_per_year and normalize
        freq_map: dict[tuple[str, str], float] = {
            k: v / years_covered for k, v in combo_counts.items()
        }
        max_freq = max(freq_map.values()) if freq_map else 1.0

        records = self._build_records(
            combo_raw_counts, freq_map, max_freq, years_covered
        )

        # Derive coverage percentage
        data_driven_count = sum(1 for r in records if r.data_driven)
        total_combos = len(_VALID_ASSET_TYPES) * len(_VALID_SCENARIOS)
        coverage_pct = (
            (data_driven_count / total_combos) * 100.0 if total_combos else 0.0
        )

        # Store calibrated matrix
        self._calibrated_matrix = {
            (r.asset_type, r.scenario): r.calibrated_score for r in records
        }

        self._report = CalibrationReport(
            total_incidents_used=total_mapped,
            date_range=date_range,
            years_covered=years_covered,
            records=records,
            coverage_pct=coverage_pct,
        )
        self._fitted = True
        return self

    def calibration_report(self) -> CalibrationReport:
        """Return calibration report. Raises RuntimeError if fit() not called."""
        if not self._fitted:
            raise RuntimeError(
                "EnigmaCalibrator.fit() must be called before calibration_report()."
            )
        return self._report  # type: ignore[return-value]

    def risk_score(self, asset_type: str, scenario: str) -> tuple[float, bool]:
        """Return (score, is_data_driven). Falls back to rule-based if unfitted."""
        rule_score = self._rule_based_score(asset_type, scenario)
        if not self._fitted:
            return rule_score, False
        key = (asset_type, scenario)
        if key in self._calibrated_matrix:
            return self._calibrated_matrix[key], True
        return rule_score, False

    def assess(self, asset_type: str, scenario: str) -> dict:
        """
        Return assessment dict compatible with EnigmaResult fields.
        Keys: asset_type, scenario, risk_score, risk_level, data_driven, confidence.
        """
        score, is_data_driven = self.risk_score(asset_type, scenario)
        confidence = self._confidence_for(asset_type, scenario)
        return {
            "asset_type": asset_type,
            "scenario": scenario,
            "risk_score": round(score, 4),
            "risk_level": _risk_level_from_score(score),
            "data_driven": is_data_driven,
            "confidence": confidence,
        }

    def calibrated_matrix_df(self) -> pd.DataFrame:
        """Return 6x6 DataFrame (asset_types x scenarios) of calibrated scores."""
        asset_types = list(_VALID_ASSET_TYPES)
        scenarios = list(_VALID_SCENARIOS)
        data = {}
        for scenario in scenarios:
            col = []
            for asset_type in asset_types:
                score, _ = self.risk_score(asset_type, scenario)
                col.append(round(score, 4))
            data[scenario] = col
        return pd.DataFrame(data, index=asset_types)

    # ------------------------------------------------------------------
    # Static helpers
    # ------------------------------------------------------------------

    @staticmethod
    def synthetic_hse_dataframe(n_incidents: int = 200) -> pd.DataFrame:
        """
        Generate a realistic synthetic HSE DataFrame for testing.
        Produces incidents with realistic equipment_type/incident_type distributions
        matching BSEE GoM historical patterns.
        """
        rng = np.random.default_rng(42)

        incident_types = ["equipment_failure", "spill", "injury", "violation"]
        incident_weights = [0.35, 0.25, 0.30, 0.10]

        equipment_types = ["bop", "crane", "fire_detection", "hipps", "safety_valve"]
        equipment_weights = [0.30, 0.20, 0.20, 0.15, 0.15]

        spill_locations = ["pipeline", "platform", "wellhead", "riser"]
        spill_weights = [0.40, 0.35, 0.15, 0.10]

        injury_types = ["fire", "structural", "dropped_object", "chemical", "slip"]
        injury_weights = [0.20, 0.20, 0.30, 0.15, 0.15]

        severities = ["fatality", "lost_time", "recordable", "near_miss", "minor"]
        severity_weights = [0.02, 0.10, 0.35, 0.30, 0.23]

        # Date range: 2015-01-01 to 2024-12-31 (~10 years)
        start_ts = pd.Timestamp("2015-01-01")
        end_ts = pd.Timestamp("2024-12-31")
        date_range_days = (end_ts - start_ts).days
        random_days = rng.integers(0, date_range_days, size=n_incidents)
        incident_dates = [start_ts + pd.Timedelta(days=int(d)) for d in random_days]

        chosen_incident_types = rng.choice(
            incident_types, size=n_incidents, p=incident_weights
        )
        chosen_severities = rng.choice(severities, size=n_incidents, p=severity_weights)

        equipment_type_col = []
        spill_location_col = []
        injury_type_col = []

        for inc_type in chosen_incident_types:
            if inc_type == "equipment_failure":
                equipment_type_col.append(
                    str(rng.choice(equipment_types, p=equipment_weights))
                )
                spill_location_col.append(None)
                injury_type_col.append(None)
            elif inc_type == "spill":
                equipment_type_col.append(None)
                spill_location_col.append(
                    str(rng.choice(spill_locations, p=spill_weights))
                )
                injury_type_col.append(None)
            elif inc_type == "injury":
                equipment_type_col.append(None)
                spill_location_col.append(None)
                injury_type_col.append(str(rng.choice(injury_types, p=injury_weights)))
            else:
                equipment_type_col.append(None)
                spill_location_col.append(None)
                injury_type_col.append(None)

        return pd.DataFrame(
            {
                "incident_type": chosen_incident_types,
                "equipment_type": equipment_type_col,
                "spill_location": spill_location_col,
                "injury_type": injury_type_col,
                "severity": chosen_severities,
                "incident_date": incident_dates,
                "operator": rng.choice(
                    ["Shell", "BP", "Chevron", "ExxonMobil", "ConocoPhillips"],
                    size=n_incidents,
                ),
                "facility_name": [
                    f"Platform_{rng.integers(1, 50)}" for _ in range(n_incidents)
                ],
            }
        )

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _map_row_to_enigma(self, row: pd.Series) -> list[tuple[str, str]]:
        """Map a single HSE incident row to ENIGMA (asset_type, scenario) pairs."""
        incident_type = str(row.get("incident_type", "")).lower()
        combos: list[tuple[str, str]] = []

        if incident_type == "equipment_failure":
            equip = str(row.get("equipment_type", "") or "").lower()
            key = ("equipment_failure", equip)
            combos = list(HSE_TO_ENIGMA_MAP.get(key, []))

        elif incident_type == "spill":
            location = str(row.get("spill_location", "") or "").lower()
            for loc_key in ("pipeline", "platform"):
                if loc_key in location:
                    combos = list(HSE_TO_ENIGMA_MAP.get(("spill", loc_key), []))
                    break

        elif incident_type == "injury":
            inj_type = str(row.get("injury_type", "") or "").lower()
            for inj_key in ("fire", "structural", "dropped_object"):
                if inj_key in inj_type:
                    combos = list(HSE_TO_ENIGMA_MAP.get(("injury", inj_key), []))
                    break

        return combos

    def _build_records(
        self,
        raw_counts: dict[tuple[str, str], int],
        freq_map: dict[tuple[str, str], float],
        max_freq: float,
        years_covered: float,
    ) -> list[CalibrationRecord]:
        """Build CalibrationRecord list for all 36 (asset, scenario) combos."""
        records = []
        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                key = (asset_type, scenario)
                count = raw_counts.get(key, 0)
                freq = freq_map.get(key, 0.0)
                rule_score = self._rule_based_score(asset_type, scenario)

                if count >= MIN_INCIDENTS_FOR_CALIBRATION:
                    raw_data_score = freq / max_freq if max_freq > 0 else 0.0
                    # Blend: 60% data, 40% rule-based
                    blended = 0.6 * raw_data_score + 0.4 * rule_score
                    calibrated = float(np.clip(blended, 0.05, 0.95))
                    data_driven = True
                    confidence = "high" if count >= 50 else "medium"
                else:
                    calibrated = rule_score
                    data_driven = False
                    confidence = "low"

                records.append(
                    CalibrationRecord(
                        asset_type=asset_type,
                        scenario=scenario,
                        incident_count=count,
                        incidents_per_year=round(freq, 4),
                        calibrated_score=round(calibrated, 4),
                        confidence=confidence,
                        data_driven=data_driven,
                    )
                )
        return records

    def _build_fallback_records(
        self, raw_counts: dict[tuple[str, str], int]
    ) -> list[CalibrationRecord]:
        """Build fully rule-based records (used when DataFrame is empty)."""
        records = []
        for asset_type in _VALID_ASSET_TYPES:
            for scenario in _VALID_SCENARIOS:
                key = (asset_type, scenario)
                count = raw_counts.get(key, 0)
                score = self._rule_based_score(asset_type, scenario)
                records.append(
                    CalibrationRecord(
                        asset_type=asset_type,
                        scenario=scenario,
                        incident_count=count,
                        incidents_per_year=0.0,
                        calibrated_score=round(score, 4),
                        confidence="low",
                        data_driven=False,
                    )
                )
        return records

    @staticmethod
    def _rule_based_score(asset_type: str, scenario: str) -> float:
        """Compute rule-based score from ENIGMA static matrices."""
        base = _SCENARIO_BASE.get(scenario, 0.5)
        modifier = _ASSET_MODIFIER.get(asset_type, 1.0)
        return float(np.clip(base * modifier, 0.0, 1.0))

    def _confidence_for(self, asset_type: str, scenario: str) -> str:
        """Return confidence label for a given combo."""
        if not self._fitted or self._report is None:
            return "low"
        for rec in self._report.records:
            if rec.asset_type == asset_type and rec.scenario == scenario:
                return rec.confidence
        return "low"

    def _parse_date_range(self, hse_df: pd.DataFrame) -> tuple[float, tuple[str, str]]:
        """Parse incident_date column; return (years_covered, (min_date, max_date))."""
        if "incident_date" not in hse_df.columns:
            return 1.0, ("", "")
        try:
            dates = pd.to_datetime(hse_df["incident_date"], errors="coerce").dropna()
            if dates.empty:
                return 1.0, ("", "")
            min_date = dates.min()
            max_date = dates.max()
            years = max((max_date - min_date).days / 365.25, 1.0)
            return years, (str(min_date.date()), str(max_date.date()))
        except Exception:
            return 1.0, ("", "")
