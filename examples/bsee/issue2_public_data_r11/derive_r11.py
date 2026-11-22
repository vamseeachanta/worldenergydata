"""Derive the revision 11 Figure 1 files from the pinned BSEE borehole file and the repository's WTI series.

Revision 11 animates Figure 1 through every five-year window from 2005 to 2009 up to 2021 to 2025, and adds the
new wells started each year by water depth with rolling averages beside the WTI oil price. The wells come from
the same borehole file as revision 9 (file of 12 November 2026, pinned by SHA-256 in
../issue2_public_data_r9/inputs/source-pins.json) under the same selection rule (build_r9.map_wells), one year
at a time. The two revision 9 map periods are re-derived and must equal revision 9 well for well.

Writes data/map-wells-by-year.csv, data/new-wells-by-year.csv and data/wti-annual.csv. Run once; build_r11.py
reads the written files (pinned in inputs/manifest.json) and needs no BSEE download.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
R9 = ROOT.parent / 'issue2_public_data_r9'
WTI = ROOT.parents[2] / 'data' / 'wti-monthly.csv'
YEARS = range(2005, 2026)
BORE = 'BoreholeRawData.zip'


def load_r9():
    spec = importlib.util.spec_from_file_location('build_r9', R9 / 'build_r9.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def wells_by_year(r9, bore):
    """Original, not cancelled Gulf boreholes spudded in each year 2005 to 2025, inside the map box (r9 rule)."""
    r9.MAP_PERIODS = [(y, y) for y in YEARS]
    wells, audit = r9.map_wells(bore)
    wells = wells.drop(columns='period').sort_values(['spud_year', 'api_well_number'], kind='stable').reset_index(drop=True)
    return wells, audit


def check_against_r9(wells):
    """The two r9 map periods, re-derived one year at a time, must equal the r9 map file well for well."""
    old = pd.read_csv(R9 / 'data' / 'map-wells.csv', dtype={'api_well_number': str})
    for (a, b), part in old.groupby(old.period.map(lambda p: tuple(int(x) for x in p.split(' to ')))):
        new = wells[wells.spud_year.between(a, b)]
        left = new[['api_well_number', 'band']].sort_values('api_well_number').reset_index(drop=True)
        right = part[['api_well_number', 'band']].sort_values('api_well_number').reset_index(drop=True)
        if not left.equals(right):
            raise ValueError(f'Re-derived wells differ from revision 9 for {a} to {b}')


def yearly_counts(wells, bands):
    table = wells.groupby(['spud_year', 'band']).size().unstack(fill_value=0).reindex(index=list(YEARS), columns=bands, fill_value=0)
    table['total'] = table.sum(axis=1)
    return table.rename_axis('year').reset_index()


def wti_annual(path=WTI):
    """Calendar-year mean of the monthly WTI spot price (EIA, Cushing), from the repository snapshot."""
    monthly = pd.read_csv(path)
    monthly['year'] = monthly.Date.str[:4].astype(int)
    part = monthly[monthly.year.isin(list(YEARS))]
    counts = part.groupby('year').size()
    if not counts.eq(12).all() or len(counts) != len(YEARS):
        raise ValueError('WTI snapshot needs twelve months in every year 2005 to 2025')
    return part.groupby('year').Price.mean().round(2).rename('wti_usd_per_bbl').reset_index()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'cache', help='folder holding BoreholeRawData.zip')
    args = parser.parse_args(argv)
    pins = json.loads((R9 / 'inputs' / 'source-pins.json').read_text(encoding='utf-8'))
    if sha(args.data_dir / BORE) != pins[BORE]:
        raise ValueError('BoreholeRawData.zip differs from the revision 9 pin (file of 12 November 2026)')
    r9 = load_r9()
    bore = r9.read_table(args.data_dir, BORE, 'mv_boreholes_all', [])
    wells, audit = wells_by_year(r9, bore)
    check_against_r9(wells)
    out = ROOT / 'data'
    out.mkdir(exist_ok=True)
    write = lambda frame, name: frame.to_csv(out / name, index=False, lineterminator='\n', float_format='%.12g')
    write(wells, 'map-wells-by-year.csv')
    counts = yearly_counts(wells, r9.BANDS)
    dropped = int(audit.missing_or_outside_coordinates.sum())
    if dropped:
        raise ValueError(f'{dropped} wells without coordinates in the map area; review the yearly counts')
    write(counts, 'new-wells-by-year.csv')
    write(wti_annual(), 'wti-annual.csv')
    print(counts.to_string(index=False))


if __name__ == '__main__':
    main()
