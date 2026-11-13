"""Offline regression cases for the newsletter's counting contract."""
import importlib.util
import math
import re
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_r8', ROOT / 'build_r8.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


@pytest.mark.parametrize('metres,index', [(0, 0), (99.9, 0), (100, 1),
    (499.9, 1), (500, 2), (1499.9, 2), (1500, 3)])
def test_band_edges_go_deeper(metres, index):
    assert build.band_from_feet(metres / .3048) == build.BANDS[index]


@pytest.mark.parametrize('value', ['', None, -1, float('nan'), float('inf')])
def test_invalid_depth_is_missing(value):
    assert build.band_from_feet(value) == 'Missing depth'


def test_positive_finite_days_and_linear_quartiles():
    data = pd.DataFrame({'activity': ['Completion'] * 8,
        'band': [build.BANDS[0]] * 8,
        'days': [1, 2, 3, 10, 0, -2, None, math.inf]})
    row = build.summarize_days(data).iloc[0]
    assert (row['n'], row['excluded_days'], row['records']) == (4, 4, 8)
    assert (row.q1_days, row.median_days, row.q3_days) == (1.75, 2.5, 4.75)
    assert row.missing_invalid_days == 2
    assert row.nonpositive_days == 2


def test_empty_cells_are_missing_not_zero():
    result = build.summarize_days(pd.DataFrame(columns=['activity', 'band', 'days']))
    assert result['n'].eq(0).all()
    assert result.median_days.isna().all()


def test_pie_years_are_fixed_complete_decades():
    assert build.pie_years(range(2005, 2027)) == [2005, 2015, 2025]
    with pytest.raises(ValueError):
        build.pie_years([2005, 2015, 2026])


@pytest.mark.parametrize('value,digits,want', [(123456, 4, '1.235e+05'),
    (0.012345, 3, '0.0123'), (100 / 47, 3, '2.13'), (0, 3, '0'),
    (None, 4, 'Not available'), (float('nan'), 4, 'Not available')])
def test_significant_figures(value, digits, want):
    assert build.significant(value, digits) == want


def test_subtype_precedence_and_unknowns():
    assert build.classify_operation('COMP', {'ZONE'}) == 'Intervention'
    assert build.classify_operation('COMP', set()) == 'Completion'
    assert build.classify_operation('ABANDON', {'TEMPABAN', 'PERMABAN'}) == 'Permanent abandonment'
    assert build.classify_operation('ABANDON', {'TEMPABAN'}) == 'Temporary abandonment'
    assert build.classify_operation('ABANDON', {'PERMABAN', 'PLUGBACK'}) == 'Excluded: new hole'
    assert build.classify_operation('ABANDON', set()).startswith('Excluded:')
    assert build.classify_operation('INFORM', set()).startswith('Excluded:')
    with pytest.raises(ValueError):
        build.classify_operation('UNKNOWN', set())


def test_conflicting_permit_duration_is_rejected():
    frame = pd.DataFrame({'SN_APM': ['1', '1'], 'EST_OPERATION_DAYS': ['2', '8']})
    with pytest.raises(ValueError, match='conflict'):
        build.unique_records(frame, 'SN_APM')


def test_actual_dates_and_full_year_filter():
    rows = pd.DataFrame({'API_WELL_NUMBER': ['1', '2', '3', '4'],
        'REGION_CODE': ['G'] * 4, 'WELL_NAME_SUFFIX': ['ST00BP00'] * 4,
        'BOREHOLE_STAT_CD': ['PA'] * 4,
        'WELL_SPUD_DATE': ['01/01/2025', '01/01/2025', '01/01/2026', 'bad'],
        'TOTAL_DEPTH_DATE': ['01/11/2025', '01/01/2025', '01/02/2026', '01/01/2025'],
        'WATER_DEPTH': ['100'] * 4})
    events, audit = build.prepare_boreholes(rows)
    assert list(events.days) == [10, 0]
    assert audit['missing_spud_date'] == 1
    assert audit['outside_years'] == 1


def test_apm_join_does_not_multiply_subtypes_or_use_ambiguous_regions():
    apm = pd.DataFrame({'SN_APM': ['a', 'a', 'b', 'c', 'd', 'e'],
        'API_WELL_NUMBER': ['1', '1', '2', '3', '4', '1'],
        'ACC_STATUS_DATE': ['01/01/2025'] * 5 + ['01/01/2026'],
        'APM_OP_CD': ['ABANDON'] * 6, 'EST_OPERATION_DAYS': ['5'] * 6,
        'WATER_DEPTH': ['100'] * 6, 'BUS_ASC_NAME': list('abcdef')})
    bore = pd.DataFrame({'API_WELL_NUMBER': ['1', '1', '2', '2', '4'],
                         'REGION_CODE': ['G', 'G', 'G', 'P', 'P']})
    sub = pd.DataFrame({'SN_APM_FK': ['a', 'a', 'a'],
                       'APM_SUBOP_CD': ['TEMPABAN', 'PERMABAN', 'PERMABAN']})
    events, audit = build.prepare_apm(apm, sub, bore)
    assert len(events) == 1
    assert events.activity.iloc[0] == 'Permanent abandonment'
    assert audit['duplicate_rows'] == 1
    assert audit['unmatched_or_ambiguous_region'] == 2
    assert audit['non_gulf'] == 1
    assert audit['outside_years'] == 1


def test_offline_cache_missing_and_tampered(tmp_path, monkeypatch):
    import json
    monkeypatch.setattr(build.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('Network access in offline test'))
    with pytest.raises(FileNotFoundError):
        build.cache_source(tmp_path, 'source.zip', 'https://example.org/source.zip', True)
    (tmp_path / 'source.zip').write_bytes(b'changed')
    (tmp_path / 'source.receipt.json').write_text(json.dumps({'url': 'https://example.org/source.zip', 'sha256': 'wrong'}))
    with pytest.raises(ValueError, match='receipt mismatch'):
        build.cache_source(tmp_path, 'source.zip', 'https://example.org/source.zip', True)


def test_issued_pin_rejects_self_consistent_substitute(tmp_path):
    import json
    p = tmp_path / 'source.zip'
    p.write_bytes(b'substitute')
    p.with_suffix('.receipt.json').write_text(json.dumps({'url': 'https://example.org/source.zip', 'sha256': build.sha(p)}))
    with pytest.raises(ValueError, match='issued source pin'):
        build.cache_source(tmp_path, p.name, 'https://example.org/source.zip', True, 'issued-digest')


def test_us_dates_do_not_swap_invalid_months():
    result = build.dates(pd.Series(['12/02/2025', '13/02/2025', '6/25/2025 7:51:41 AM']))
    assert result.iloc[0] == pd.Timestamp('2025-12-02')
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pd.Timestamp('2025-06-25 07:51:41')


def test_large_count_display_marks_rounding():
    assert build.count_display(23216) == '≈23,220'
    assert build.count_display(4410) == '4,410'


def test_latest_key_sensitivity_keeps_last_date_not_last_input_row():
    frame = pd.DataFrame({'SN_APM': ['2', '1'], 'API_WELL_NUMBER': ['A', 'A'],
        'APM_OP_CD': ['WORKOVER', 'WORKOVER'],
        'ACC_STATUS_DATE': ['12/01/2025', '01/01/2025'],
        'activity': ['Intervention'] * 2, 'band': [build.BANDS[0]] * 2,
        'days': [10, 2]})
    row = build.latest_key_sensitivity(frame).query("activity == 'Intervention'").iloc[0]
    assert row.n == 2 and row.median_days == 6
    assert row.latest_key_n == 1 and row.latest_key_median_days == 10


def test_table1_html_csv_and_annual_counts_agree():
    from html.parser import HTMLParser
    class Cells(HTMLParser):
        def __init__(self):
            super().__init__()
            self.rows, self.row, self.cell = [], [], None
        def handle_starttag(self, tag, attrs):
            if tag == 'tr': self.row = []
            if tag in ['td', 'th']: self.cell = ''
        def handle_data(self, value):
            if self.cell is not None: self.cell += value
        def handle_endtag(self, tag):
            if tag in ['td', 'th']:
                self.row.append(self.cell)
                self.cell = None
            if tag == 'tr': self.rows.append(self.row)
    page = (ROOT / 'issue2-public-data-r8.html').read_text(encoding='utf-8')
    cells = Cells()
    cells.feed(re.search(r'<table>.*?</table>', page, re.S)[0])
    table = pd.read_csv(ROOT / 'data/table1.csv', dtype=str, keep_default_na=False)
    assert cells.rows == [list(table.columns)] + table.values.tolist()
    rig = pd.read_csv(ROOT / 'data/fig-p1-new-well-permits-by-rig-type.csv')
    depth = pd.read_csv(ROOT / 'data/new-well-permits-by-water-depth-r7.csv')
    for i, category in enumerate(build.RIGS):
        assert int(table.iloc[i, 1].replace(',', '')) == rig[category].sum()
    for i, column in enumerate(build.WK):
        assert int(table.iloc[-1, i + 2].replace(',', '')) == depth[column].sum()


def test_r7_count_conservation_and_exact_pies():
    rig = pd.read_csv(ROOT / 'data/fig-p1-new-well-permits-by-rig-type.csv')
    depth = pd.read_csv(ROOT / 'data/new-well-permits-by-water-depth-r7.csv')
    assert rig.total.sum() == 2895
    assert rig[build.RIGS].sum(axis=1).equals(rig.total)
    assert depth[build.WK].sum(axis=1).equals(depth.permits)
    assert rig.total.equals(depth.permits)
    for kind, frame, keys in [('rig', rig, build.RIGS), ('depth', depth, build.WK)]:
        pies = pd.read_csv(ROOT / f'data/pies-{kind}.csv')
        for year in [2005, 2015, 2025]:
            values = list(frame[frame.year.eq(year)][keys].iloc[0])
            assert list(pies[pies.year.eq(year)].permits) == values


def test_rendered_html_contract():
    page = (ROOT / 'issue2-public-data-r8.html').read_text(encoding='utf-8')
    page = re.sub(r'<script\b[^>]*>.*?</script>', '', page, flags=re.S)
    assert 'Some of the observations are as follows:' in page
    assert re.search(r'Some of the observations are as follows:</p>\s*<ul>', page)
    assert 'Appendix A Reusable prompts' in page
    headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', page)
    assert all(re.match(r'(\d+(\.\d+)? |B\.\d+ |Appendix [AB] )', h) for h in headings)
    assert not re.search(r'[A-Z]:[\\/]|file://|/mnt/|/Users/', page)
    assert not re.search(r'\b(acceptable|conservative|safe)\b', page, re.I)
    assert page.count('Our hypothesis:') == 2
    assert '2026 is partial' in page
    assert 'EST_OPERATION_DAYS' in page
    assert 'TOTAL_DEPTH_DATE' in page
    assert '.viz{display:none}' in page


def rendered_prose():
    page = (ROOT / 'issue2-public-data-r8.html').read_text(encoding='utf-8')
    return re.sub(r'<script\b[^>]*>.*?</script>', '', page, flags=re.S)


def test_section3_observations_read_csv_and_match_page(tmp_path):
    stats = pd.read_csv(ROOT / 'data/days-summary.csv')
    def medians(activity):
        return stats[stats.activity.eq(activity) & stats.band.isin(build.BANDS)].median_days
    completion, drilling = medians('Completion'), medians('Spud to total depth')
    intervention, abandonment = medians('Intervention'), medians('Permanent abandonment')
    expected = [
        f'Completion estimate medians rise with water depth, from {completion.iloc[0]:g} d under 100 m to {completion.iloc[-1]:g} d at 1,500 m and deeper.',
        f'Recorded spud-to-total-depth medians rise with water depth, from {drilling.iloc[0]:g} d under 100 m to {drilling.iloc[-1]:g} d at 1,500 m and deeper.',
        f'Across the four depth bands, intervention estimate medians range from {intervention.min():g} to {intervention.max():g} d; permanent-abandonment estimate medians range from {abandonment.min():g} to {abandonment.max():g} d.',
    ]
    assert build.day_observations(ROOT / 'data/days-summary.csv') == expected
    section = rendered_prose().split('<h3>3.1 ')[1].split('<h3>3.2 ')[0]
    assert re.findall(r'<li>(.*?)</li>', section, re.S) == expected
    stats.loc[stats.activity.eq('Completion') & stats.band.eq(build.BANDS[0]), 'median_days'] = 11
    changed = tmp_path / 'days.csv'
    stats.to_csv(changed, index=False)
    assert 'from 11 d' in build.day_observations(changed)[0]


def test_body_rules_are_short_and_details_are_in_appendix_b():
    page = rendered_prose()
    rules = page.split('<h3>3.2 ')[1].split('<h3>3.3 ')[0]
    bullets = re.findall(r'<li>(.*?)</li>', rules, re.S)
    assert len(bullets) == 5
    assert all(len(re.sub('<[^>]+>', '', b).split()) <= 30 for b in bullets)
    assert rules.count('href="#counting-rules"') == 1
    body, appendix = page.split('<h2 id="counting-rules">')
    for detail in ['SN_APM', 'ZONE', 'PERMABAN', 'PLUGBACK', 'REGION_CODE', 'ST00BP00', 'Selection counts before day exclusions', 'repeat-key sensitivity check']:
        assert detail not in body.split('<h2>3 ')[1].split('<h2 id="reusable-prompts">')[0]
        assert detail in appendix
    assert page.index('Appendix A Reusable prompts') < page.index('Appendix B Counting rules and record counts for section 3')


def test_body_table_is_six_columns_with_full_audit_in_appendix():
    page = rendered_prose()
    body, appendix = page.split('<h2 id="counting-rules">')
    table = re.findall(r'<table>.*?</table>', body, re.S)[1]
    assert re.findall(r'<th\b[^>]*>(.*?)</th>', table) == ['Activity and basis', 'Water depth', 'Used (-)', 'Q1 (d)', 'Median (d)', 'Q3 (d)']
    assert table.count('<tr>') == 21
    assert 'Missing depth' not in table
    assert 'Every selected record has a water depth.' in body
    assert 'Missing/invalid (-)' in appendix and 'Nonpositive (-)' in appendix
    assert 'Missing depth' in appendix


def test_closing_paragraphs_move_unchanged_after_figure3():
    import os
    import subprocess
    old = subprocess.run(['git', 'show', 'c7fc424d:examples/bsee/issue2_public_data_r8/inputs/page-template.html'],
        cwd=ROOT, capture_output=True, check=True, encoding='utf-8',
        creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        env={k: v for k, v in os.environ.items() if k not in {'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR'}}).stdout
    page = rendered_prose()
    paragraphs = re.findall(r'<p(?: class="q")?>(?:Our hypothesis:|To try it out|Each count here).*?</p>', old)
    assert len(paragraphs) == 4
    assert '\n'.join(paragraphs) in page
    for paragraph in paragraphs:
        assert page.count(paragraph) == 1
        assert page.index('Figure 3 -') < page.index(paragraph) < page.index('<p>If you have run your own analysis')


def test_page_dates_captions_and_concise_review_panel():
    page = rendered_prose()
    assert not re.search(r'\d{4}-\d{2}-\d{2}|\(UTC\)', re.sub(r'<style.*?</style>', '', page, flags=re.S))
    source = 'Source: BSEE Application for Permit to Drill raw data (<a href="https://www.data.bsee.gov/Well/Files/APDRawData.zip">APDRawData.zip</a>), file of 2 November 2026, retrieved 3 November 2026. Data:'
    assert page.count(source) == 9
    assert '<sup>a</sup>' not in page
    assert page.count('Types with no permits in that year are not shown.') == 6
    panel = page.split('<div class="review-panel">')[1].split('</div>')[0]
    assert panel.count('<li>') == 6
    assert 'Section 3 data: operator estimates (APM) and recorded spud-to-total-depth dates (borehole files), retrieved 13 November 2026; the APD file has no estimated drilling days.' in panel
    assert not re.search(r'pull/|gate run|[0-9a-f]{40}', panel, re.I)
    assert not (ROOT / 'review-plan.html').exists()


def test_pie_payload_and_static_labels_skip_zero_use_one_decimal(tmp_path, monkeypatch):
    captured = {}
    def capture(fig, out, name):
        if name.startswith('pie-'):
            captured[name] = ([t.get_text() for t in fig.axes[0].get_legend().get_texts()],
                              [t.get_text() for t in fig.axes[0].texts if t.get_text()])
        build.plt.close(fig)
    monkeypatch.setattr(build, 'save_figure', capture)
    (tmp_path / 'data').mkdir()
    rig = pd.read_csv(ROOT / 'inputs/fig-p1-new-well-permits-by-rig-type.csv')
    depth = pd.read_csv(ROOT / 'inputs/new-well-permits-by-water-depth-r7.csv')
    payload = build.count_figures(rig, depth, tmp_path)
    for chart in payload:
        if chart['kind'] != 'pie':
            continue
        assert all(v > 0 for v in chart['values'])
        assert chart['shares'] == [f'{v / chart["total"] * 100:.1f}%' for v in chart['values']]
        legends, labels = captured[chart['id']]
        assert legends == [f'{label}: {share}' for label, share in zip(chart['labels'], chart['shares'])]
        assert labels == chart['shares']


def test_depth_statement_fails_closed_for_new_missing_depth():
    stats = pd.read_csv(ROOT / 'data/days-summary.csv')
    stats.loc[stats.band.eq('Missing depth'), 'records'] = 1
    with pytest.raises(ValueError, match='missing depth'):
        build.days_table(stats)


def test_range_observation_rejects_a_missing_band_median(tmp_path):
    stats = pd.read_csv(ROOT / 'data/days-summary.csv')
    stats.loc[stats.activity.eq('Intervention') & stats.band.eq(build.BANDS[0]), 'median_days'] = float('nan')
    path = tmp_path / 'days.csv'
    stats.to_csv(path, index=False)
    with pytest.raises(ValueError, match='four depth bands'):
        build.day_observations(path)
