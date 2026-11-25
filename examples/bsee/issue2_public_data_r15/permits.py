"""Recount r12 permit tables from APD rows using the article's rawdata_fact_check selector."""
from collections import Counter, defaultdict
from statistics import median

import pandas as pd

from issue2_public_data_r9.build_r9 import BANDS, FT_TO_M, PIE_YEARS, WK, band_from_feet
from rawdata_fact_check import count_rawdata as apd


PERMIT_YEARS = range(2005, 2027)


def depth_summary(depths):
    """Return counts in the r12 band order and median water depth rounded to whole metres."""
    counts = Counter(band for _, band in depths)
    median_m = round(median(ft for ft, _ in depths) * FT_TO_M) if depths else None
    return [counts[band] for band in BANDS], median_m


def pie_rows(frame, count_columns, labels):
    """Tabular part of build_r12.pie_set, including the zero-count slices."""
    records = []
    for year in PIE_YEARS:
        row = frame.loc[frame.year.eq(year)].iloc[0]
        total = sum(int(row[col]) for col in count_columns)
        for col, label in zip(count_columns, labels):
            n = int(row[col])
            records.append(dict(year=year, category=label, permits=n, total=total,
                                share_percent=n / total * 100 if total else None))
    return pd.DataFrame(records)


def permit_tables(rows):
    """Build the five permit tables and return the disjoint reasons APD source rows were excluded."""
    first = apd.first_new_well_permits(rows)
    counts = apd.count_permits(first, PERMIT_YEARS.start, PERMIT_YEARS[-1])
    rig = pd.DataFrame(counts['by_year'])

    # Apply the Gulf / New Well / API filters in order so each rejected row has a single reason.
    gulf = sum(r['REGION_CODE'].strip() == 'G' for r in rows)
    gulf_new = [r for r in rows if apd.is_gulf_new_well(r)]
    missing_api = sum(not r['API_WELL_NUMBER'].strip() for r in gulf_new)
    excluded = dict(non_gulf=len(rows) - gulf, not_new_well=gulf - len(gulf_new),
                    missing_api_well_number=missing_api,
                    later_or_duplicate_permit=len(gulf_new) - missing_api - len(first),
                    no_spud_date=counts['no_spud_date'], outside_years=0)

    by_year, by_rig = defaultdict(list), defaultdict(list)
    for row in first:
        date = apd.mdy(row['REQ_SPUD_DATE'])
        if not date:
            continue
        if date[0] not in PERMIT_YEARS:
            excluded['outside_years'] += 1
            continue
        ft = row['WATER_DEPTH']
        band = band_from_feet(ft)
        if band == 'Missing depth':
            raise ValueError(f"Missing or invalid depth for selected API {row['API_WELL_NUMBER']}")
        depth = (float(ft), band)
        by_year[date[0]].append(depth)
        by_rig[apd.rig_label(row['RIG_TYPE_CODE'])].append(depth)

    annual = []
    for year in PERMIT_YEARS:
        bands, median_m = depth_summary(by_year[year])
        annual.append(dict(year=year, permits=len(by_year[year]), **dict(zip(WK, bands)), median_m=median_m))
    depth = pd.DataFrame(annual)

    # Table 1 prints thousands separators and leaves the pooled median blank.
    columns = ['Rig type', 'New-well permits, 2005 to 2026 (-)',
               *(f'{band} (-)' for band in BANDS), 'Median water depth (m)']
    summary = []
    for label in apd.LABELS:
        bands, median_m = depth_summary(by_rig[label])
        summary.append([label, f"{counts['totals'][label]:,}", *(f'{n:,}' for n in bands),
                        '' if median_m is None else f'{median_m:,}'])
    summary.append(['All', f"{counts['all']:,}", *(f'{depth[col].sum():,}' for col in WK), ''])
    tables = {
        'fig-p1-new-well-permits-by-rig-type': rig,
        'new-well-permits-by-water-depth': depth,
        'table1': pd.DataFrame(summary, columns=columns),
        'pies-rig': pie_rows(rig, apd.LABELS, apd.LABELS),
        'pies-depth': pie_rows(depth, WK, BANDS),
    }
    return tables, excluded
