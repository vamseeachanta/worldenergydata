"""Offline source-normalization example using explicitly synthetic inputs.

Method: the two known monthly values sum to 10.5 + 2.5 = 13.0 bbl. The third
value is unknown, so the subtotal cannot establish complete field production.
Column and unit source: ANH oil metadata, produccion_bls description, read
2026-10-20: https://www.datos.gov.co/api/views/fdvb-hsrf.json.
Run from the repository root: PYTHONPATH=src python examples/international_sources.py
"""

import json
from decimal import Decimal

from worldenergydata.international_sources.colombia import normalize_rows


def worked_example() -> dict:
    """Inputs, method and answer are deterministic; no source is contacted."""
    inputs = [
        {
            "campo": "EXAMPLE",
            "vigencia": "2024",
            "mes": "2",
            "contrato": contract,
            "produccion_bls": volume,
        }
        for contract, volume in [("A", "10.5"), ("B", "2.5"), ("C", None)]
    ]
    observations = normalize_rows(inputs, commodity="oil")
    known = [row.volume for row in observations if row.volume is not None]
    return {
        "basis": "synthetic demonstration; no live production",
        "known_subtotal_bbl": str(sum(known, Decimal(0))),
        "unknown_volume_count": sum(row.volume is None for row in observations),
        "production_status": "NOT_EVALUATED",
        "period": observations[0].period,
    }


if __name__ == "__main__":
    print(json.dumps(worked_example(), indent=2))
