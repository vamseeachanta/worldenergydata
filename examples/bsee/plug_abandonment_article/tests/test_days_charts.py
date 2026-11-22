"""The parked section 3 code still draws Figures 6 and 7 and gives the revision 10 observations."""
import importlib.util
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
R10 = ROOT.parent / 'issue2_public_data_r10'
spec = importlib.util.spec_from_file_location('days_charts', ROOT / 'days_charts.py')
days = importlib.util.module_from_spec(spec)
spec.loader.exec_module(days)


def test_parked_data_equals_revision_10():
    for name in ['days-summary.csv', 'days-overview.csv']:
        assert (ROOT / 'data' / name).read_bytes() == (R10 / 'data' / name).read_bytes(), name


def test_charts_and_tables_rebuild(tmp_path):
    days.main(['--output-dir', str(tmp_path)])
    names = ['days-overview-stage', 'days-overview-depth'] + ['days-' + days.STAGES[a][0] for a in days.ACTIVITIES]
    for name in names:
        assert (tmp_path / 'figures' / (name + '.png')).stat().st_size > 0
    assert pd.read_csv(tmp_path / 'data' / 'days-overview.csv').equals(pd.read_csv(ROOT / 'data' / 'days-overview.csv'))
    assert 'Table' not in (tmp_path / 'table-b1.html').read_text(encoding='utf-8')[:20]


def test_observations_match_the_parked_text():
    text = (ROOT / 'section3-days.md').read_text(encoding='utf-8').replace('\n  ', ' ')
    for line in days.day_observations(ROOT / 'data' / 'days-summary.csv'):
        assert line in text, line
