"""Local registry inputs and immutable Parquet snapshots with provenance."""

from __future__ import annotations

import hashlib
import json
import zipfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from worldenergydata.texas_rrc.operators.registry import RegistryPolicy, RegistryResult
from worldenergydata.texas_rrc.source_catalog import SOURCE_CATALOG_ROOT

REGISTRY_DIR = Path("curated/operators/operator_registry")
# PDQLoader.PRODUCTION_FIELD_MAPPING and production_atlas.sources column names.
ALIASES = {
    "operator_number": "operator_no",
    "og_oper_no": "operator_no",
    "oper_no": "operator_no",
    "og_oper_name": "operator_name",
    "oper_name": "operator_name",
    "lease_number": "lease_no",
    "og_lease_no": "lease_no",
    "district_no": "district",
    "og_dist_no": "district",
    "dist_no": "district",
    "county_code": "county",
    "county_no": "county",
    "og_county_no": "county",
    "field_number": "field_no",
    "og_field_no": "field_no",
    "api_number": "well_id",
    "api_no": "well_id",
    "api14": "well_id",
    "production_date": "production_month",
    "og_cycle": "production_month",
    "cycle_year_month": "production_month",
    "oil_production": "oil_bbl",
    "og_oil_prod": "oil_bbl",
    "lease_oil_prod_vol": "oil_bbl",
    "gas_production": "gas_mcf",
    "og_gas_prod": "gas_mcf",
    "lease_gas_prod_vol": "gas_mcf",
    "water_production": "water_bbl",
    "og_water_prod": "water_bbl",
    "lease_water_prod_vol": "water_bbl",
}


@dataclass
class OperatorInputs:
    """Two selected local snapshots, with input byte digests."""

    production: pd.DataFrame
    wells: pd.DataFrame
    provenance: list[dict]


def _digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def _read_csv(handle) -> pd.DataFrame:
    # Same native DSV separators as production_atlas.sources._separator.
    first_line = handle.readline()
    if isinstance(first_line, bytes):
        first_line = first_line.decode("utf-8-sig")
    handle.seek(0)
    separator = next((sep for sep in ("}", "|", ",", "\t") if sep in first_line), None)
    return pd.read_csv(
        handle, sep=separator, engine="python", dtype=str, keep_default_na=False
    )


def _read_table(path: Path, production: bool) -> pd.DataFrame:
    if path.suffix.lower() == ".parquet":
        return pd.read_parquet(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as archive:
            names = [
                name
                for name in archive.namelist()
                if Path(name).suffix.lower() in {".csv", ".txt", ".dsv"}
            ]
            if production:
                names = [
                    name
                    for name in names
                    if "OG_LEASE_CYCLE_DATA_TABLE" in name.upper()
                ]
            if len(names) != 1:
                raise ValueError(
                    "Select exactly one lease-cycle or well inventory table"
                )
            with archive.open(names[0]) as handle:
                return _read_csv(handle)
    if path.suffix.lower() not in {".csv", ".txt", ".dsv"}:
        raise ValueError(
            "Inputs must be local CSV, DSV, Parquet or selected ZIP tables"
        )
    with path.open(encoding="utf-8-sig") as handle:
        return _read_csv(handle)


def normalize_input_columns(frame: pd.DataFrame) -> pd.DataFrame:
    """Preserve string IDs; aliases never infer well status or ownership.

    A native lease-cycle table without operator names/IDs must first be joined
    to the appropriate dated reference table; current inventory cannot supply
    historical operator attribution. Canonical gas_mcf is already total gas;
    only explicit native gas components are summed, and casinghead is consumed.
    """
    source = frame.rename(columns=lambda column: str(column).strip().lower())
    renamed = source.rename(columns=ALIASES)
    if renamed.columns.duplicated().any():
        raise ValueError(
            "Ambiguous input aliases: multiple columns for one canonical name"
        )
    if "production_month" in renamed:
        renamed["production_month"] = renamed.production_month.astype(str).str.replace(
            r"^(\d{4})(\d{2})$", r"\1-\2", regex=True
        )
    elif {"cycle_year", "cycle_month"}.issubset(renamed.columns):
        renamed["production_month"] = (
            renamed.cycle_year.astype(str)
            + "-"
            + renamed.cycle_month.astype(str).str.zfill(2)
        )
    if "lease_csgd_prod_vol" in renamed and "gas_mcf" not in source:
        if "lease_gas_prod_vol" not in source:
            raise ValueError(
                "Casinghead gas requires explicit native gas components "
                "or a canonical gas_mcf total"
            )
        # RRC PDQ FAQ, crude oil vs condensate: keep liquids separate;
        # total gas includes separately reported casinghead gas without BOE conversion.
        # Validate each component before summing; missing gas remains unknown.
        for column in ("gas_mcf", "lease_csgd_prod_vol"):
            raw = renamed[column].mask(renamed[column].eq(""))
            values = pd.to_numeric(raw, errors="raise")
            if (
                (values < 0)
                | (
                    values.notna()
                    & ~values.map(lambda x: float("-inf") < x < float("inf"))
                )
            ).any():
                raise ValueError("Invalid gas component")
            renamed[column] = values
        renamed["gas_mcf"] = renamed.gas_mcf + renamed.lease_csgd_prod_vol
        renamed = renamed.drop(columns="lease_csgd_prod_vol")
    return renamed


def load_operator_inputs(
    production_path: Path | str, wells_path: Path | str
) -> OperatorInputs:
    """Read selected landed files; never download or combine snapshot revisions."""
    paths = [Path(production_path), Path(wells_path)]
    frames = [
        normalize_input_columns(_read_table(path, index == 0))
        for index, path in enumerate(paths)
    ]
    provenance = [
        {"source_id": source, "input_name": path.name, "sha256": _digest(path)}
        for source, path in zip(("production_pdq", "wellbore_query"), paths)
    ]
    return OperatorInputs(*frames, provenance)


def write_operator_registry(
    result: RegistryResult,
    output_root: Path | str,
    policy: RegistryPolicy,
    *,
    inputs: list[dict] | None = None,
    code_revision: str | None = None,
    allow_non_catalog_root: bool = False,
) -> Path:
    """Write a fresh storage-contract directory; existing data is never replaced.

    For another run, select a fresh snapshot root. Manifest is written last;
    absence of a manifest means an incomplete write, not a reusable snapshot.
    """
    root = Path(output_root).resolve()
    if not allow_non_catalog_root and not root.is_relative_to(
        SOURCE_CATALOG_ROOT.resolve()
    ):
        raise ValueError("output_root must be under the catalog root")
    target = root / REGISTRY_DIR
    target.mkdir(parents=True, exist_ok=False)
    parquet = target / "operator_registry.parquet"
    result.registry.to_parquet(parquet, index=False)
    quality = target / "quality.json"
    quality.write_text(
        json.dumps(result.quality, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": len(result.registry),
        "policy": asdict(policy),
        "inputs": inputs or [],
        "code_revision": code_revision,
        "code_revision_status": "recorded" if code_revision else "NOT_EVALUATED",
        "source_ids": result.quality["source_ids"],
        "outputs": {
            path.name: {"sha256": _digest(path), "byte_size": path.stat().st_size}
            for path in (parquet, quality)
        },
        "methods": "operator-registry-v1",
        "limitations": [
            "Operator of record is the filer; working-interest ownership is unknown.",
            "Oil production is per lease; oil-well BOPD and stripper share are NOT_EVALUATED.",
            "Per-well gas statistics cover eligible gas wells only; see coverage counts.",
            "Last12 totals are observed sums; usable_last12 flags complete coverage.",
        ],
    }
    manifest = target / "manifest.json"
    manifest.write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n"
    )
    return manifest
