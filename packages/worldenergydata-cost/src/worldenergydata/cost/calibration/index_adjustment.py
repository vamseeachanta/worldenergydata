"""One public-index snapshot with cached source-year to basis-year factors."""

from hashlib import sha256
from pathlib import Path

from worldenergydata.cost.escalation import CostEscalator, EscalationFactor, _year
from worldenergydata.cost.timeseries.dataset import read_timeseries_csv

DEFAULT_INDEX_PATH = Path("data/modules/cost/curated/cost_component_timeseries.csv")


class IndexAdjustment:
    """Retain factors, notes and traces; divide by the same factor to invert.

    File inputs retain a byte digest. Without an explicit input the curated path
    is relative to the working directory. No fallback or network fetch is added.
    """

    def __init__(self, index_path=None, *, escalator: CostEscalator | None = None):
        if index_path is not None and escalator is not None:
            raise ValueError("supply either an index path or an escalator")
        self.csv_sha256: str | None = None
        if escalator is None:
            path = Path(index_path) if index_path is not None else DEFAULT_INDEX_PATH
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

    def factor(self, source_year, base_year) -> EscalationFactor:
        """Validate before cache lookup, including same-year and boolean inputs."""
        key = (_year(source_year), _year(base_year))
        if key not in self.factors:
            self.factors[key] = self.escalator.factor(*key, public_only=True)
        return self.factors[key]
