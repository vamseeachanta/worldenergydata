"""Run the shipped offline example without invoking any remote endpoint."""

import json
import runpy
from pathlib import Path


def test_worked_example_matches_the_written_hand_calculation(capsys):
    """Synthetic known values total 10.5 + 2.5 = 13.0; one value is unknown.

    The unknown is counted separately. A known subtotal is not a field total.
    """
    root = Path(__file__).resolve().parents[3]
    runpy.run_path(str(root / "examples/international_sources.py"), run_name="__main__")
    assert json.loads(capsys.readouterr().out) == {
        "basis": "synthetic demonstration; no live production",
        "known_subtotal_bbl": "13.0",
        "unknown_volume_count": 1,
        "production_status": "NOT_EVALUATED",
        "period": "2024-02",
    }
