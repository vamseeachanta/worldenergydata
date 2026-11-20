"""One public-index snapshot with cached source-year to basis-year factors."""

from hashlib import sha256
from os import PathLike
from pathlib import Path

from worldenergydata.common.data_resolver import DataNotFoundError, get_module_data
from worldenergydata.cost.escalation import (
    CostEscalator,
    EscalationFactor,
    validate_year,
)
from worldenergydata.cost.timeseries.dataset import TIMESERIES_CSV, read_timeseries_csv


def default_index_path() -> Path:
    """Return the curated index CSV under the resolved cost module data folder.

    Resolved at call time through ``get_module_data("cost")``: ``WED_DATA_ROOT``
    first, then the workspace ``data`` folder located from the installed source,
    so the result does not depend on the working directory.
    """
    try:
        return get_module_data("cost") / "curated" / TIMESERIES_CSV
    except DataNotFoundError as exc:
        raise FileNotFoundError(
            f"index CSV missing; supply index_path or escalator ({exc})"
        ) from exc


class IndexAdjustment:
    """Retain factors, notes and traces; divide by the same factor to invert.

    File inputs retain a byte digest. Without an explicit input the curated CSV
    is resolved by ``default_index_path``. No fallback or network fetch is added.
    """

    def __init__(
        self,
        index_path: str | PathLike[str] | None = None,
        *,
        escalator: CostEscalator | None = None,
    ) -> None:
        if index_path is not None and escalator is not None:
            raise ValueError("supply either an index path or an escalator")
        self.csv_sha256: str | None = None
        if escalator is None:
            path = Path(index_path) if index_path is not None else default_index_path()
            if not path.is_file():
                raise FileNotFoundError(
                    "index CSV missing; supply index_path or escalator"
                )
            self.csv_sha256 = sha256(path.read_bytes()).hexdigest()
            escalator = CostEscalator(read_timeseries_csv(path))
            if sha256(path.read_bytes()).hexdigest() != self.csv_sha256:
                raise ValueError("index CSV changed while loading")
        self.escalator = escalator
        self.factors: dict[tuple[int, int], EscalationFactor] = {}

    def factor(self, source_year: object, base_year: object) -> EscalationFactor:
        """Validate before cache lookup, including same-year and boolean inputs."""
        key = (validate_year(source_year), validate_year(base_year))
        if key not in self.factors:
            self.factors[key] = self.escalator.factor(*key, public_only=True)
        return self.factors[key]
