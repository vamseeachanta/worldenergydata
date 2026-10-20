"""Observed SENER production to the shared country and FDAS contracts."""

from __future__ import annotations

import numpy as np

from worldenergydata.fdas.adapters.contract import FdasInputs, to_fdas_production
from worldenergydata.production.unified.adapters.base import AbstractProductionAdapter
from worldenergydata.production.unified.query import STANDARD_COLUMNS, ProductionQuery

from .bulk import ProductionWorkbook


class SenerProductionAdapter(AbstractProductionAdapter):
    """Explicit observed-data alternative to the existing illustrative adapter.

    Named fields spanning multiple basin/location identities are rejected rather
    than accidentally combined. Operator contributions within one identity are
    summed only when every contributing measurement is present.
    """

    region = "mexico"

    def __init__(self, workbook: ProductionWorkbook, *, basin=None, location=None):
        self.workbook = workbook
        self._data = workbook.production.copy(deep=True)
        self.basin, self.location = basin, location
        if basin is not None:
            self._data = self._data[self._data.basin == basin]
        if location is not None:
            self._data = self._data[self._data.location == location]
        if self._data.empty:
            raise ValueError("no observations match the requested basin/location")
        identities = self._data[["field_name", "basin", "location"]].drop_duplicates()
        if identities.field_name.duplicated().any():
            raise ValueError(
                "ambiguous field names require a reviewed identity crosswalk"
            )

    def fetch(self, query: ProductionQuery):
        frame = self._data.copy()
        if self.region not in query.regions:
            return self._empty_frame()
        frame = self._filter_by_fields(frame, query.fields)
        frame = self._filter_by_date(frame, query.start, query.end)
        if frame.empty:
            return self._empty_frame()
        metrics = ["oil_bbl", "gas_mcf", "water_bbl", "condensate_bbl"]
        frame = frame.groupby(["field_name", "year", "month"], as_index=False)[
            metrics
        ].agg(lambda values: values.sum(min_count=len(values)))
        frame["region"] = self.region
        frame["source"] = "sener_field_production"
        return frame[list(STANDARD_COLUMNS)].reset_index(drop=True)

    def available_fields(self):
        return sorted(self._data.field_name.unique().tolist())

    def date_range(self):
        dates = self._data.date
        return dates.min().strftime("%Y-%m"), dates.max().strftime("%Y-%m")

    def fdas_inputs(self, *, water_bbl: dict | None = None) -> FdasInputs:
        """Require explicit field-month water measurements; never assume zero.

        ``water_bbl`` keys are (field_name, year, month). Supplied water values
        are caller inputs, not regulator observations; the bundle records this.
        No missing gas/oil is imputed. Condensate is not sold as petroleum.
        """
        frame = self.fetch(ProductionQuery(regions=[self.region]))
        if water_bbl is None:
            raise ValueError(
                "water production is unavailable; supply field-month water_bbl"
            )
        frame["water_bbl"] = [
            water_bbl.get((r.field_name, r.year, r.month), np.nan)
            for r in frame.itertuples()
        ]
        if any(isinstance(value, (bool, np.bool_)) for value in frame.water_bbl):
            raise ValueError("water must be a measurement, not a boolean")
        values = frame[["oil_bbl", "gas_mcf", "water_bbl"]].to_numpy(dtype=float)
        if not np.isfinite(values).all() or (values < 0).any():
            raise ValueError(
                "oil, gas and water must be complete, finite and non-negative"
            )
        return FdasInputs(
            production=to_fdas_production(frame),
            region=self.region,
            metadata={
                "sha256": self.workbook.sha256,
                "vintage": self.workbook.vintage,
                "water_source": "caller_supplied",
                "basin": self.basin,
                "location": self.location,
                "condensate": "excluded",
                "fiscal_readiness": "NOT_EVALUATED",
            },
        )
