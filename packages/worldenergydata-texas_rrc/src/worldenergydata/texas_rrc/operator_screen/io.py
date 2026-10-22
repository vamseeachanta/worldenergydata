"""Local JSON input and deterministic CSV, Parquet, HTML and manifest outputs."""

import csv
import hashlib
import json
from pathlib import Path

from .report import render_onepager


def load_bundle(path: Path | str) -> dict:
    """Read a normalized local snapshot; identifiers must be JSON strings."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_outputs(result: dict, output: Path | str, operator_no: str | None = None):
    """Publish artifacts locally; no downloads, allocation or browser execution.

    PyArrow is an existing Texas RRC package dependency, imported only for export.
    Manifests contain digests and dataset provenance, without local input paths.
    """
    import pyarrow as pa
    import pyarrow.parquet as pq

    if operator_no is not None and operator_no not in {
        o["operator_no"] for o in result["operators"]
    }:
        raise KeyError("operator is absent from registry")
    target = Path(output)
    target.mkdir(parents=True, exist_ok=True)
    artifacts = []
    for name, rows in (
        ("operator_registry", result["operators"]),
        ("ranked_operators", result["ranked_operators"]),
        ("ranked_candidates", result["candidates"]),
    ):
        json_path = target / f"{name}.json"
        json_path.write_text(
            json.dumps(rows, indent=2, sort_keys=True, allow_nan=False) + "\n"
        )
        artifacts.append(json_path)
        csv_path = target / f"{name}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream, fieldnames=list(rows[0]) if rows else ["operator_no"]
            )
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        k: (
                            "NOT_EVALUATED"
                            if v is None
                            else json.dumps(v) if isinstance(v, (list, dict)) else v
                        )
                        for k, v in row.items()
                    }
                )
        parquet_path = target / f"{name}.parquet"
        table = (
            pa.Table.from_pylist(rows)
            if rows
            else pa.table({"operator_no": pa.array([], type=pa.string())})
        )
        pq.write_table(table, parquet_path)
        artifacts.extend([csv_path, parquet_path])
    report_dir = target / "operators"
    report_dir.mkdir(exist_ok=True)
    for row in result["operators"]:
        if operator_no is not None and row["operator_no"] != operator_no:
            continue
        path = report_dir / f'{row["operator_no"]}.html'
        path.write_text(render_onepager(result, row["operator_no"]), encoding="utf-8")
        artifacts.append(path)
    manifest = {
        k: v
        for k, v in result.items()
        if k not in {"operators", "ranked_operators", "candidates"}
    }
    manifest["artifacts"] = {
        path.relative_to(target)
        .as_posix(): hashlib.sha256(path.read_bytes())
        .hexdigest()
        for path in artifacts
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def normalize_pdq_rows(rows) -> list[dict]:
    """Adapt OG_LEASE_CYCLE rows from the existing PDQ member reader.

    Source: RRC PDQ Dump Manual, OG_LEASE_CYCLE, pp. 12–13 and field
    descriptions LEASE_GAS_PROD_VOL / LEASE_CSGD_PROD_VOL. Gas total combines
    gas-well and casinghead Mcf. Oil excludes condensate. No water is in this
    table. O/G IDs remain regulator reporting units, never API allocations.
    Unfiled reports are omitted, so their months remain unknown.
    """
    from .core import _month, _text, _volume

    output = []
    for raw in rows:
        row = {
            "district": _text(raw, "DISTRICT_NO"),
            "oil_gas_code": _text(raw, "OIL_GAS_CODE"),
            "lease_no": _text(raw, "LEASE_NO"),
            "operator_no": _text(raw, "OPERATOR_NO"),
            "granularity": "lease",
        }
        cycle = _text(raw, "CYCLE_YEAR_MONTH")
        month = cycle[:4] + "-" + cycle[4:]
        _month(month)
        flag = _text(raw, "PROD_REPORT_FILED_FLAG")
        if flag not in {"Y", "N"}:
            raise ValueError("unrecognized report-filed flag")
        if flag == "N":
            continue
        values = {}
        for key in ("LEASE_OIL_PROD_VOL", "LEASE_GAS_PROD_VOL", "LEASE_CSGD_PROD_VOL"):
            text = raw.get(key)
            if text is None or text == "" or isinstance(text, bool):
                raise ValueError("PDQ production volume is missing")
            values[key] = _volume({key: float(text)}, key)
        row.update(
            month=month,
            oil_bbl=values["LEASE_OIL_PROD_VOL"],
            gas_mcf=values["LEASE_GAS_PROD_VOL"] + values["LEASE_CSGD_PROD_VOL"],
            water_bbl=None,
        )
        output.append(row)
    return output
