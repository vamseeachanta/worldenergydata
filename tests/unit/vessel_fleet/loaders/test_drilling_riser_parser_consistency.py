"""Reject parser disagreement before literal identities can be misassigned."""

from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from worldenergydata.vessel_fleet.loaders.drilling_riser_loader import (
    DrillingRiserLoader,
)


def write_catalog(directory: Path) -> None:
    """Use two synthetic records with distinct identities and provenance."""
    content = (
        "COMPONENT_ID,DATA_SOURCE,NOTES,COMPONENT_TYPE,OD_IN,"
        "PRESSURE_RATING_PSI,BORE_SIZE_IN,BOP_TYPE,MANUFACTURER\n"
        "01,Synthetic source,First record,riser_joint,,,,,\n"
        "NA,Synthetic source,Second record,riser_joint,,,,,\n"
    )
    (directory / "drilling_riser_components.csv").write_bytes(content.encode("utf-8"))


@pytest.mark.parametrize("parsed_rows", [0, 1, 3])
def test_parser_count_mismatch_is_not_cached_and_allows_retry(
    tmp_path: Path, parsed_rows: int
) -> None:
    """Neither dropped nor additional pandas rows may populate the cache."""
    write_catalog(tmp_path)
    loader = DrillingRiserLoader(tmp_path)
    path = tmp_path / "drilling_riser_components.csv"
    frame = pd.read_csv(path)
    parsed = frame.iloc[[0] * parsed_rows].reset_index(drop=True)
    with patch("pandas.read_csv", return_value=parsed):
        with pytest.raises(
            ValueError,
            match=rf"CSV parser row count mismatch: strict reader=2, pandas={parsed_rows}$",
        ):
            loader.load()
    assert loader._df is None
    assert loader.load()["COMPONENT_ID"].tolist() == ["01", "NA"]


def test_literal_id_assignment_uses_row_position(tmp_path: Path) -> None:
    """Index labels cannot move literal IDs away from their parsed records."""
    write_catalog(tmp_path)
    frame = pd.read_csv(tmp_path / "drilling_riser_components.csv")
    frame.index = [1, 0]
    with patch("pandas.read_csv", return_value=frame):
        result = DrillingRiserLoader(tmp_path).load()
    assert result["COMPONENT_ID"].tolist() == ["01", "NA"]
    assert result["NOTES"].tolist() == ["First record", "Second record"]
