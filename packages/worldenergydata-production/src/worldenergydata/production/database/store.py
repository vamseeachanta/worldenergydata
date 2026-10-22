"""SQLite catalog with atomic, immutable normalized production snapshots."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from datetime import date
from importlib.resources import files
from numbers import Integral
from pathlib import Path

from .models import (
    CANONICAL_UNITS,
    REGULATOR_SOURCES,
    DeclineHistory,
    SourceSnapshot,
    number,
    text,
)


class ProductionDatabase:
    """An offline store; opening a database never fetches regulator data.

    Each ingest consumes one complete normalized snapshot. No revisions are
    overwritten, no field identities are inferred and no unit conversion occurs.
    The caller owns raw-source retention, source rights and engineering review.
    """

    def __init__(self, path: str | Path):
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA foreign_keys = ON")
        try:
            version = self._db.execute("PRAGMA user_version").fetchone()[0]
            if version == 0:
                if self._db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchone():
                    raise ValueError("refusing an unversioned nonempty database")
                schema = (
                    files(__package__)
                    .joinpath("schema.sql")
                    .read_text(encoding="utf-8")
                )
                self._db.executescript(schema)
            elif version != 1:
                raise ValueError("unsupported production database version")
        except Exception:
            self._db.close()
            raise

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def close(self):
        """Release the database; each public write has its own transaction."""
        self._db.close()

    def _one(self, query, parameters, name):
        row = self._db.execute(query, parameters).fetchone()
        if row is None:
            raise ValueError(f"unknown {name}")
        return dict(row)

    def source_snapshot(self, snapshot_id: str) -> dict:
        return self._one(
            "SELECT * FROM snapshots WHERE snapshot_id = ?", (snapshot_id,), "snapshot"
        )

    def _asset(self, asset_id: str) -> dict:
        return self._one(
            "SELECT * FROM assets WHERE asset_id = ?", (asset_id,), "asset"
        )

    def add_snapshot(self, snapshot: SourceSnapshot):
        """Retain caller-attested source metadata without replacing prior evidence."""
        if not isinstance(snapshot, SourceSnapshot):
            raise TypeError("snapshot must be SourceSnapshot")
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                    tuple(asdict(snapshot).values()),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate snapshot") from error

    def add_asset(self, asset_id: str, name: str, kind: str):
        """Catalog a field, facility, reservoir or explicitly non-field aggregate."""
        text(asset_id, "asset_id")
        text(name, "name")
        if kind not in {"field", "facility", "reservoir", "aggregate"}:
            raise ValueError("invalid asset kind")
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO assets VALUES (?, ?, ?)", (asset_id, name, kind)
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate asset") from error

    def link_asset(self, field_id: str, child_id: str):
        """Link shared facilities or reservoirs to fields without merging identities."""
        if self._asset(field_id)["kind"] != "field":
            raise ValueError("parent must be a field")
        if self._asset(child_id)["kind"] not in {"facility", "reservoir"}:
            raise ValueError("child must be a facility or reservoir")
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO asset_links VALUES (?, ?)", (field_id, child_id)
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate asset link") from error

    def linked_assets(self, field_id: str) -> list[dict]:
        self._asset(field_id)
        rows = self._db.execute(
            "SELECT a.* FROM assets a JOIN asset_links l ON a.asset_id = l.child_id "
            "WHERE l.field_id = ? ORDER BY a.asset_id",
            (field_id,),
        )
        return [dict(row) for row in rows]

    def map_field(self, source_id: str, external_id: str, asset_id: str):
        """Explicitly map the adapter's exact field_name token to a catalog asset.

        Names are not globally unique IDs. Different regulator aliases are
        independent assertions; aggregate series retain their distinct kind.
        """
        if source_id not in REGULATOR_SOURCES.values():
            raise ValueError("unknown regulator source_id")
        text(external_id, "external_id")
        if self._asset(asset_id)["kind"] not in {"field", "aggregate"}:
            raise ValueError("production mappings require a field or aggregate")
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO field_mappings VALUES (?, ?, ?)",
                    (source_id, external_id, asset_id),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate field mapping") from error

    def ingest(
        self, snapshot_id: str, records: Iterable[Mapping], *, units: Mapping
    ) -> int:
        """Ingest unified STANDARD_COLUMNS rows in one rollback-capable transaction.

        Unknown values are explicit None. NaN and infinity are rejected so that
        malformed measurements cannot silently become missing data.
        """
        if dict(units) != dict(CANONICAL_UNITS):
            raise ValueError("units must match the canonical monthly-volume units")
        count = 0
        try:
            with self._db:
                # Serialize the loaded check and inserts across concurrent connections.
                self._db.execute("BEGIN IMMEDIATE")
                snapshot = self.source_snapshot(snapshot_id)
                if snapshot["loaded"]:
                    raise ValueError(
                        "snapshot is already loaded; register another version"
                    )
                for record in records:
                    values = self._production_values(snapshot, record)
                    self._db.execute(
                        "INSERT INTO regulator_production VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        values,
                    )
                    count += 1
                if not count:
                    raise ValueError("empty production snapshot")
                self._db.execute(
                    "UPDATE snapshots SET loaded = 1 WHERE snapshot_id = ?",
                    (snapshot_id,),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate production row") from error
        return count

    def _production_values(self, snapshot: dict, row: Mapping) -> tuple:
        required = {"region", "field_name", "year", "month", "source", *CANONICAL_UNITS}
        if not isinstance(row, Mapping) or not required.issubset(row):
            raise ValueError("missing unified production columns")
        year, month = row["year"], row["month"]
        if any(
            isinstance(v, bool) or not isinstance(v, Integral) for v in (year, month)
        ):
            raise ValueError("year and month must be integers")
        try:
            date(year, month, 1)
            period = f"{year:04d}-{month:02d}"
        except (ValueError, OverflowError) as error:
            raise ValueError("invalid production period") from error
        external_id = text(row["field_name"], "field_name")
        asset = self._one(
            "SELECT asset_id FROM field_mappings WHERE source_id = ? AND external_id = ?",
            (snapshot["source_id"], external_id),
            "field mapping",
        )
        label = text(row["source"], "source")
        if snapshot["data_kind"] != "synthetic" and any(
            token in label.lower() for token in ("mock", "synthetic")
        ):
            raise ValueError("synthetic adapter rows require a synthetic snapshot")
        volumes = tuple(
            None if row[key] is None else number(row[key], key)
            for key in CANONICAL_UNITS
        )
        return (
            snapshot["snapshot_id"],
            asset["asset_id"],
            period,
            text(row["region"], "region"),
            external_id,
            label,
            *volumes,
        )

    def production(self, snapshot_id: str, asset_id: str) -> list[dict]:
        """Return one asset and vintage; never sum competing regulator reports."""
        self.source_snapshot(snapshot_id)
        self._asset(asset_id)
        rows = self._db.execute(
            "SELECT * FROM regulator_production WHERE snapshot_id = ? AND asset_id = ? "
            "ORDER BY period",
            (snapshot_id, asset_id),
        )
        return [dict(row) for row in rows]

    def decline_history(
        self, snapshot_id: str, asset_id: str, *, allow_synthetic: bool = False
    ) -> DeclineHistory:
        """Prepare contiguous positive oil volumes for the existing monthly fitter.

        No day normalization, first-month exclusion or engineering qualification
        is implied. The caller must assess those conditions before fitting.
        """
        snapshot = self.source_snapshot(snapshot_id)
        if self._asset(asset_id)["kind"] != "field":
            raise ValueError("decline histories require a field, not an aggregate")
        if snapshot["data_kind"] == "synthetic" and not allow_synthetic:
            raise ValueError("synthetic history requires explicit opt-in")
        rows = self.production(snapshot_id, asset_id)
        if not rows:
            raise ValueError("no production history")
        previous = None
        points = []
        for index, row in enumerate(rows, start=1):
            year, month = map(int, row["period"].split("-"))
            # Gregorian calendar: twelve months per year; this is an ordinal,
            # not a duration or a production-rate conversion.
            ordinal = year * 12 + month
            if previous is not None and ordinal != previous + 1:
                raise ValueError("production history has missing calendar months")
            points.append((index, number(row["oil_bbl"], "oil_bbl", positive=True)))
            previous = ordinal
        payload = {"snapshot": snapshot, "asset_id": asset_id, "rows": rows}
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
            ensure_ascii=False,
        )
        digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
        return DeclineHistory(
            snapshot_id, asset_id, tuple(points), digest, snapshot["data_kind"]
        )

    def save_decline(
        self,
        curve_id: str,
        history: DeclineHistory,
        *,
        model: str,
        qi: float,
        di: float,
        b: float,
        method_ref: str,
    ):
        """Store supplied fit parameters, bound to the exact retained history.

        Parameter convention: EIA, Production Decline Curve Analysis (2023),
        hyperbolic equation: q(t)=qi/(1+b*Di*t)**(1/b). Exponential b=0 is
        the limiting form; harmonic b=1 follows by substitution. No fitted
        parameter, economic cutoff or acceptance threshold is supplied here.
        """
        text(curve_id, "curve_id")
        text(method_ref, "method_ref")
        expected = self.decline_history(
            history.snapshot_id,
            history.asset_id,
            allow_synthetic=history.data_kind == "synthetic",
        )
        if expected != history:
            raise ValueError("history does not match stored production evidence")
        qi, di, b = (
            number(qi, "qi", positive=True),
            number(di, "di", positive=True),
            number(b, "b"),
        )
        if model not in {"exponential", "hyperbolic", "harmonic"}:
            raise ValueError("unknown decline model")
        if (
            (model == "exponential" and b != 0)
            or (model == "harmonic" and b != 1)
            or (model == "hyperbolic" and b == 0)
        ):
            raise ValueError("decline exponent does not match model")
        origin = self.production(history.snapshot_id, history.asset_id)[0]["period"]
        try:
            with self._db:
                self._db.execute(
                    "INSERT INTO decline_curves VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        curve_id,
                        history.snapshot_id,
                        history.asset_id,
                        model,
                        qi,
                        di,
                        b,
                        "bbl/month",
                        origin,
                        history.sha256,
                        method_ref,
                        "NOT_EVALUATED",
                    ),
                )
        except sqlite3.IntegrityError as error:
            raise ValueError("duplicate decline curve") from error

    def decline_curve(self, curve_id: str) -> dict:
        """Read curve parameters together with source vintage and synthetic status."""
        return self._one(
            "SELECT c.*, s.version AS source_version, s.source_id, s.data_kind, "
            "s.sha256 AS source_sha256 FROM decline_curves c "
            "JOIN snapshots s ON c.snapshot_id = s.snapshot_id WHERE c.curve_id = ?",
            (curve_id,),
            "decline curve",
        )
