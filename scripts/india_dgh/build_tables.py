"""Build the shipped India tables from the reviewed public source files.

Usage:
    python scripts/india_dgh/build_tables.py --raw data/modules/india_dgh/raw

The committed raw copies are the default input; ``fetch_sources.py`` re-downloads
them into an empty directory and checks their digests.

Every input file is checked against the SHA-256 in ``source_manifest.json``
before it is parsed; a changed file stops the build. Outputs are written to
``packages/worldenergydata-india_dgh/src/worldenergydata/india_dgh/data``.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from worldenergydata.india_dgh.basins import parse_basin_page
from worldenergydata.india_dgh.blocks import COLUMNS, RoundSource, parse_round_pdf
from worldenergydata.india_dgh.production import (
    combine,
    parse_ppac_gas_sheet,
    parse_ppac_sheet,
    read_sheets,
)
from worldenergydata.india_dgh.sources import data_path, load_source_manifest, verify_file

# Award lists. Signing dates only where the cited document states them:
# round IV press release of 2 Jan 2020 ("signed today"); rounds VII and IX
# award lists ("RSC signed on 28.06.2022", "RSC signed on 15.04.2025").
ROUNDS = [
    RoundSource("OALP-I", "OALP", "dgh_oalp1_awardees"),
    RoundSource("OALP-II", "OALP", "dgh_oalp2_awardees"),
    RoundSource("OALP-III", "OALP", "dgh_oalp3_awardees"),
    RoundSource("OALP-IV", "OALP", "dgh_oalp4_contract_signing", "2020-01-02"),
    RoundSource("OALP-V", "OALP", "dgh_oalp5_blocks_awarded"),
    RoundSource("OALP-VI", "OALP", "dgh_oalp6_awardees"),
    RoundSource("OALP-VII", "OALP", "dgh_oalp7_awardees", "2022-06-28"),
    RoundSource("OALP-VIII", "OALP", "dgh_oalp8_blocks_awarded"),
    RoundSource("OALP-IX", "OALP", "dgh_oalp9_awardees", "2025-04-15"),
    RoundSource("SCBM-2022", "CBM", "dgh_scbm2022_blocks_awarded"),
]
# Offer lists that publish block area for rounds whose award list omits it.
OFFER_AREAS = [RoundSource("OALP-IX", "OALP", "dgh_oalp9_blocks_on_offer")]
BASIN_PAGE = "dgh_basins_and_categories"
# Listed oldest capture first: a later capture supersedes an earlier one for the
# same period (provisional years are revised in later editions).
CRUDE = ["ppac_crude_annual_2019", "ppac_crude_annual_hindi_2022", "ppac_crude_current_2022"]
GAS = ["ppac_gas_historical_2020", "ppac_gas_current_2022"]


def _verified(raw: Path, source_id: str) -> Path:
    entry = {e["id"]: e for e in load_source_manifest()["files"]}[source_id]
    path = raw / entry["filename"]
    verify_file(path, source_id)
    return path


def build_blocks(raw: Path) -> pd.DataFrame:
    frame = pd.concat([parse_round_pdf(_verified(raw, s.source_id), s) for s in ROUNDS], ignore_index=True)
    for source in OFFER_AREAS:
        offer = parse_round_pdf(_verified(raw, source.source_id), source)
        areas = offer.set_index("block_name").area_km2.dropna()
        target = (frame["round"] == source.round) & frame.area_km2.isna() & frame.block_name.isin(areas.index)
        frame.loc[target, "area_km2"] = frame.loc[target, "block_name"].map(areas)
        frame.loc[target, "area_basis"] = "offer_list"
    if frame.block_name.duplicated().any():
        raise ValueError("a block appears in more than one round")
    return frame[COLUMNS]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw", type=Path, required=True)
    args = parser.parse_args(argv)
    out = data_path("")
    blocks = build_blocks(args.raw)
    blocks.to_csv(out / "awarded_blocks.csv", index=False, lineterminator="\n")
    basins = parse_basin_page(_verified(args.raw, BASIN_PAGE).read_bytes())
    basins.to_csv(out / "basins.csv", index=False, lineterminator="\n")
    print(f"awarded_blocks.csv {len(blocks)} rows; basins.csv {len(basins)} rows")
    frames = [
        parse_ppac_sheet(sheet, "crude_oil", s)
        for s in CRUDE
        for sheet in read_sheets(_verified(args.raw, s))
    ]
    frames += [
        parse_ppac_gas_sheet(sheet, s)
        for s in GAS
        for sheet in read_sheets(_verified(args.raw, s), month_wise_only=True)
    ]
    production = combine(frames)
    production.to_csv(out / "production.csv", index=False, lineterminator="\n")
    print(f"production.csv {len(production)} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())
