"""Hand-counted Gulf APD selection, depth bands and published table denominators."""
import sys
from pathlib import Path

import pytest

BSEE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BSEE))
from issue2_public_data_r15.permits import permit_tables


def permit(api, sn, year, depth_ft, rig='JACKUP', region='G', kind='New Well'):
    return {
        'API_WELL_NUMBER': api, 'SN_APD': str(sn), 'PERMIT_TYPE': kind,
        'REGION_CODE': region, 'REQ_SPUD_DATE': f'1/1/{year}' if year else '',
        'WATER_DEPTH': str(depth_ft), 'RIG_TYPE_CODE': rig,
    }


def test_first_permit_year_limits_and_exclusive_reasons():
    rows = [
        permit('001', 10, 2006, 20),
        permit('001', 2, 2005, 100, rig=' drillship '),
        permit('002', 3, 2015, 10),
        permit('003', 4, 2025, 10),
        permit('004', 5, 2026, 10, rig='BARGE'),
        permit('005', 6, None, 10),
        permit('005', 7, 2006, 10),
        permit('006', 8, 2005, 10, region='P', kind='Revised'),
        permit('007', 9, 2005, 10, kind='Revised'),
        permit(' ', 11, 2005, 10),
        permit('008', 12, 2004, 10),
        permit('009', 13, 2027, 10),
    ]
    tables, excluded = permit_tables(rows)
    rig = tables['fig-p1-new-well-permits-by-rig-type'].set_index('year')
    depth = tables['new-well-permits-by-water-depth'].set_index('year')
    assert list(rig.index) == list(range(2005, 2027))
    assert rig.loc[2005, 'Drillship'] == rig.loc[2026, 'Other'] == 1
    assert rig.loc[2006, 'total'] == 0
    assert rig.total.equals(rig.drop(columns='total').sum(axis=1))
    assert rig.total.equals(depth.permits)
    assert rig.total.equals(depth.drop(columns=['permits', 'median_m']).sum(axis=1))
    assert excluded == {
        'non_gulf': 1, 'not_new_well': 1, 'missing_api_well_number': 1,
        'later_or_duplicate_permit': 2, 'no_spud_date': 1, 'outside_years': 2,
    }
    assert len(rows) == rig.total.sum() + sum(excluded.values())


def test_band_edges_rounding_and_share_denominators():
    rows = [
        permit('a', 1, 2005, 1),
        permit('b', 2, 2005, 100 / 0.3048),
        permit('c', 3, 2005, 500 / 0.3048, rig='DRILLSHIP'),
        permit('d', 4, 2015, 1500 / 0.3048, rig='DRILLSHIP'),
        permit('e', 5, 2025, 0, rig='UNKNOWN'),
    ]
    tables, _ = permit_tables(rows)
    depth = tables['new-well-permits-by-water-depth'].set_index('year')
    assert depth.loc[2005].tolist() == [3, 1, 1, 1, 0, 100]
    assert depth.loc[2015, '1500_m_and_deeper'] == 1
    assert depth.loc[2025, 'under_100_m'] == 1
    assert depth.loc[2025, 'median_m'] == 0
    table = tables['table1'].set_index('Rig type')
    assert table.loc['All'].tolist() == ['5', '2', '1', '1', '1', '']
    assert table.loc['Drillship', 'Median water depth (m)'] == '1,000'
    assert table.loc['Jack-up', 'Median water depth (m)'] == '50'
    for kind, categories in [('rig', 7), ('depth', 4)]:
        pies = tables[f'pies-{kind}']
        assert list(pies.year.unique()) == [2005, 2015, 2025]
        assert len(pies) == 3 * categories
        assert pies.groupby('year').permits.sum().tolist() == [3, 1, 1]
        assert pies.groupby('year').share_percent.sum().tolist() == pytest.approx([100] * 3)
    shares = tables['pies-rig'].set_index(['year', 'category'])
    assert shares.loc[(2005, 'Jack-up'), 'share_percent'] == pytest.approx(200 / 3)
