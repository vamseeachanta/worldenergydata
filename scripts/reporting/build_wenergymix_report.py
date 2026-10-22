"""Build the offline offshore-wind module report from public interfaces.

Rebuild from the repository root:
    PYTHONPATH=src python scripts/reporting/build_wenergymix_report.py
"""

import argparse
import csv
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path

from worldenergydata.energy_mix.irena import (
    COLUMNS,
    MAX_EXPORT_BYTES,
    emit_manifest,
    load_export,
)
from worldenergydata.energy_mix.query import GWH_TO_MWH, query_export

ROOT = Path(__file__).resolve().parents[2]
REPORT_DIR = ROOT / "docs/reports/modules/wenergymix"
FIXTURE = ROOT / "tests/fixtures/energy_mix/irena_offshore_synthetic.csv"


def csv_rows(raw: bytes) -> list[dict[str, str]]:
    """Read the module's CSV bytes without rounding supplied observations."""
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8"))))


def calculate_example() -> dict:
    """Call the module on the documented synthetic fixture and zero variation."""
    raw = FIXTURE.read_bytes()
    records = load_export(raw)
    original = csv_rows(raw)
    converted = csv_rows(query_export(raw, generation_unit="MWh"))
    first = original[0]
    selected = csv_rows(
        query_export(
            raw,
            countries=[first["country"].casefold()],
            start_year=records[0]["year"],
            end_year=records[0]["year"],
            generation_unit="MWh",
        )
    )
    variation = [{**row} for row in original]
    variation[0]["generation_gwh"] = "0"
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=first.keys(), lineterminator="\n")
    writer.writeheader()
    writer.writerows(variation)
    zero = csv_rows(
        query_export(buffer.getvalue().encode("utf-8"), generation_unit="MWh")
    )
    return {
        "original": original,
        "converted": converted,
        "selected": selected,
        "zero": zero,
        "manifest": json.loads(emit_manifest(raw, synthetic=True)),
    }


def report_data() -> dict:
    """Collect exact display strings and calculation-source identities."""
    example = calculate_example()
    original, converted = example["original"], example["converted"]
    metrics = {
        "alpha_gwh": original[0]["generation_gwh"],
        "alpha_mwh": converted[0]["generation_mwh"],
        "beta_gwh": original[2]["generation_gwh"],
        "beta_mwh": converted[2]["generation_mwh"],
        "zero_gwh": "0",
        "zero_mwh": example["zero"][0]["generation_mwh"],
        "conversion": str(GWH_TO_MWH),
        "input_rows": str(len(original)),
        "selected_rows": str(len(example["selected"])),
        "source_bytes": str(example["manifest"]["size_bytes"]),
        "max_bytes": str(MAX_EXPORT_BYTES),
        "clock_year": str(datetime.now(timezone.utc).year),
        "column_count": str(len(COLUMNS)),
    }
    for index, row in enumerate(original):
        for field in ("year", "capacity_mw", "generation_gwh"):
            if row[field]:
                metrics[f"row_{index}_{field}"] = row[field]
        if converted[index]["generation_mwh"]:
            metrics[f"row_{index}_generation_mwh"] = converted[index]["generation_mwh"]
    package = ROOT / "src/worldenergydata/energy_mix"
    digests = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(package.glob("*.py"))
    }
    return {"example": example, "metrics": metrics, "source_digests": digests}


def metric(key: str, data: dict) -> str:
    """Mark numerical text so consistency tests can inspect every occurrence."""
    return f'<span data-metric="{key}">{escape(data["metrics"][key])}</span>'


def example_rows(data: dict) -> str:
    """Render source and returned fields, keeping missing cells descriptive."""
    rows = []
    for index, row in enumerate(data["example"]["original"]):
        fields = [escape(row["country"])]
        for field in ("year", "capacity_mw", "generation_gwh", "generation_mwh"):
            key = f"row_{index}_{field}"
            fields.append(
                metric(key, data) if key in data["metrics"] else "Unavailable"
            )
        fields.append('<a href="#ref-example">Published synthetic example</a>')
        rows.append("<tr>" + "".join(f"<td>{value}</td>" for value in fields) + "</tr>")
    return "\n".join(rows)


def build_report(output: Path = REPORT_DIR / "index.html") -> Path:
    """Write one self-contained HTML file; source fixtures remain read-only."""
    data = report_data()
    changes = json.loads((REPORT_DIR / "changes.json").read_text(encoding="utf-8"))
    template = (REPORT_DIR / "report.template.html").read_text(encoding="utf-8")
    substitutions = {
        "style": (REPORT_DIR / "house-style.css").read_text(encoding="utf-8"),
        "interactions": (REPORT_DIR / "interactions.js").read_text(encoding="utf-8"),
        "data": json.dumps(
            data, ensure_ascii=False, sort_keys=True, allow_nan=False
        ).replace("<", "\\u003c"),
        "rows": example_rows(data),
        "input_csv": escape(FIXTURE.read_text(encoding="utf-8").rstrip()),
        "digest": escape(data["example"]["manifest"]["sha256"]),
        "sources": "".join(
            f"<li><code>{escape(path)}</code>: <code>{digest}</code></li>"
            for path, digest in data["source_digests"].items()
        ),
        "changes": "".join(
            f"<li>{escape(change)}</li>"
            for change in changes["revisions"][0]["changes"]
        ),
    }
    text = re.sub(
        r"@@metric:([a-z_0-9]+)@@", lambda match: metric(match[1], data), template
    )
    for key, value in substitutions.items():
        text = text.replace(f"@@{key}@@", value)
    binding = hashlib.sha256(text.encode("utf-8")).hexdigest()
    text = text.replace("@@binding@@", binding)
    if "@@" in text:
        raise ValueError("Unresolved report placeholder")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(text, encoding="utf-8", newline="\n")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=REPORT_DIR / "index.html")
    build_report(parser.parse_args().output)
