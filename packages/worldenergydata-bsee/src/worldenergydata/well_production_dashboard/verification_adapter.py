"""Connect dashboard observations to the validation and persisted audit APIs."""

import json
from numbers import Real
from threading import RLock

import numpy as np
import pandas as pd

from worldenergydata.bsee.analysis.well_data_verification import (
    VerificationConfig,
    VerificationWorkflow,
)
from worldenergydata.bsee.analysis.well_data_verification.audit import AuditLogger
from worldenergydata.bsee.analysis.well_data_verification.quality import (
    DataQualityFramework,
    QualityConfig,
)
from worldenergydata.validation.schemas import DataType, FieldSchema, ValidationSchema

REQUIRED_COLUMNS = ("well_id", "date", "oil_production")


def valid_score(value):
    """A missing or non-finite score cannot satisfy a quality criterion."""
    return (
        isinstance(value, Real)
        and not isinstance(value, (bool, np.bool_))
        and np.isfinite(value)
        and 0 <= value <= 1
    )


class DashboardVerification:
    """Assess supplied observations; physical units and limits are not inferred."""

    def __init__(self, db_path, threshold):
        if not valid_score(threshold):
            raise ValueError(
                "Quality threshold must be a finite value from zero to one"
            )
        if not db_path:
            raise ValueError("An explicit audit database path is required")
        self.threshold = threshold
        self.lock = RLock()
        schema = ValidationSchema(name="dashboard observations")
        for field in (
            FieldSchema("well_id", DataType.STRING, min_length=1),
            FieldSchema("date", DataType.DATETIME),
            FieldSchema("oil_production", DataType.FLOAT),
        ):
            schema.add_field(field)
        self.workflow = VerificationWorkflow(
            schema=schema, config=VerificationConfig(), strict=False
        )
        self.quality = DataQualityFramework(
            QualityConfig(required_fields=list(REQUIRED_COLUMNS))
        )
        self.audit = AuditLogger(db_path)
        self.audit.database.close()

    @staticmethod
    def prepare(data):
        """Reject missing observations and ambiguous dates before validation."""
        if not isinstance(data, pd.DataFrame) or data.empty:
            raise ValueError("Nonempty observations are required")
        if not data.columns.is_unique or not set(REQUIRED_COLUMNS) <= set(data.columns):
            raise ValueError("Unique required observation columns are required")
        frame = data.copy()
        ids = frame["well_id"]
        if not ids.map(
            lambda value: isinstance(value, str) and bool(value.strip())
        ).all():
            raise ValueError("Nonblank well identifiers are required")
        if ids.nunique() != 1:
            raise ValueError("Verification requires observations for one well")
        dates = frame["date"]
        if dates.isna().any() or dates.map(lambda value: isinstance(value, Real)).any():
            raise ValueError("Explicit observation dates are required")
        frame["date"] = pd.to_datetime(dates, errors="raise")
        if frame["date"].isna().any():
            raise ValueError("Valid observation dates are required")
        for column in frame.columns:
            if column in ("well_id", "date", "verification_status"):
                continue
            series = frame[column]
            measurement = column in {
                "oil_production",
                "gas_production",
                "water_production",
                "operating_days",
            }
            if measurement or pd.api.types.is_numeric_dtype(series):
                if series.map(lambda value: isinstance(value, (bool, np.bool_))).any():
                    raise ValueError(
                        "Boolean observations are not numeric measurements"
                    )
                numeric = pd.to_numeric(series, errors="raise")
                if not np.isfinite(numeric.to_numpy(dtype=float)).all():
                    raise ValueError("Finite observations are required")
                frame[column] = numeric
        return frame

    def assess(self, data):
        """Publish a result only after its audit record is read back."""
        with self.lock:
            frame = self.prepare(data)
            validation_frame = frame.copy()
            validation_frame["date"] = frame["date"].map(
                lambda value: value.isoformat()
            )
            valid, errors = self.workflow.validate(validation_frame)
            quality = self.quality.run_quality_checks(frame)
            score = quality.metadata.get("quality_score")
            if not valid_score(score):
                raise ValueError("A finite quality score from zero to one is required")
            verified = valid and quality.is_valid and score >= self.threshold
            result = {
                "status": "verified" if verified else "failed",
                "quality_score": float(score),
                "quality_threshold": self.threshold,
                "scope": "supplied observation structure and data quality",
                "row_count": len(frame),
                "anomalies": [error.message for error in errors],
                "data_completeness": float(frame.notna().to_numpy().mean()),
            }
            self._persist(frame["well_id"].iloc[0], result)
            return result

    def _persist(self, well_id, result):
        details = {"well_id": well_id, **result}
        try:
            event = self.audit.log_event("verification", "dashboard", details)
            rows = self.audit.database.query(
                "SELECT details FROM audit_events WHERE event_id = ?", (event.event_id,)
            )
            if len(rows) != 1 or json.loads(rows[0]["details"]) != details:
                raise RuntimeError("Verification audit readback did not match")
            result["audit_trail_id"] = event.event_id
            result["verification_date"] = event.timestamp
        finally:
            self.audit.database.close()

    def history(self, well_id):
        """Filter the complete event stream rather than a globally capped subset."""
        with self.lock:
            try:
                events = self.audit.query_events(event_type="verification", limit=None)
                records = [
                    {
                        "timestamp": event.timestamp,
                        "action": event.event_type,
                        "user": event.user_id,
                        "details": event.details,
                    }
                    for event in events
                    if event.details.get("well_id") == well_id
                ]
                return pd.DataFrame(
                    records, columns=["timestamp", "action", "user", "details"]
                )
            finally:
                self.audit.database.close()
