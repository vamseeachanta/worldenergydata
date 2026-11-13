"""Offline regression cases for the newsletter's counting contract and the r9 page layout."""
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
import urllib.request
from fractions import Fraction
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / 'issue2-public-data-r9.html'
spec = importlib.util.spec_from_file_location('build_r9', ROOT / 'build_r9.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
FOLDER = 'issue2_public_data_r9'
BUILD_FILE = 'build_r9.py'
PAGE_FILE = ROOT / 'issue2-public-data-r9.html'

CHART_HARNESS = r"""
const input = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const plots = [], restyles = [], results = [], els = {}, touched = [];
const el = id => els[id] || (els[id] = {id, style: {}, clientWidth: 900, handlers: {},
  on(name, f) { this.handlers[name] = f; }});
global.window = {};
global.getComputedStyle = () => ({getPropertyValue: () => ' #123456 '});
global.document = {documentElement: {}, querySelectorAll: () => [],
  getElementById: id => { touched.push(id); return el(id); },
  querySelector: () => ({hidden: false})};
if (input.plotly) {
  global.Plotly = {Plots: {resize() {}},
    newPlot(e, traces, layout) { plots.push({id: e.id, traces, layout}); return Promise.resolve(); },
    restyle(e, update) { restyles.push({id: e.id, visible: update.visible}); return Promise.resolve(); }};
}
new Function(input.script)();
setTimeout(() => {
  for (const [id, name, data] of input.events) results.push(el(id).handlers[name](data));
  process.stdout.write(JSON.stringify({plots, restyles, results, touched}));
}, 0);
"""


def run_chart_script(script, events=(), plotly=True):
    """Run the page's chart script in Node with a recording Plotly stand-in and replay legend and button events."""
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js is needed for the chart interaction test')
    done = subprocess.run([node, '-e', CHART_HARNESS],
                          input=json.dumps({'script': script, 'events': list(events), 'plotly': plotly}),
                          capture_output=True, text=True, encoding='utf-8', timeout=120, check=True)
    return json.loads(done.stdout)


def chart_script():
    scripts = re.findall(r'<script>(\s*\(function\(\)\{.*?)</script>', PAGE_FILE.read_text(encoding='utf-8'), re.S)
    assert len(scripts) == 1
    return scripts[0]


def raw_page():
    return PAGE.read_text(encoding='utf-8')


def rendered_prose():
    return re.sub(r'<script\b[^>]*>.*?</script>', '', raw_page(), flags=re.S)


def chart_payload():
    script = re.findall(r"<script>\s*\(function\(\)\{\s*if\(typeof Plotly==='undefined'\)return;\s*const charts=(.*?);\n", raw_page(), re.S)
    assert len(script) == 1
    return json.loads(script[0])


# Counting contract carried from r8 -----------------------------------------------------------

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
    row = build.summarize_days(data).query("activity == 'Completion'").iloc[0]
    # Hand check: usable days 1, 2, 3, 10; linear quartiles 1.75, 2.5, 4.75.
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


def borehole_rows(**columns):
    n = len(next(iter(columns.values())))
    base = {'API_WELL_NUMBER': [str(i) for i in range(n)], 'REGION_CODE': ['G'] * n,
            'WELL_NAME_SUFFIX': ['ST00BP00'] * n, 'BOREHOLE_STAT_CD': ['PA'] * n,
            'WELL_SPUD_DATE': ['01/01/2025'] * n, 'TOTAL_DEPTH_DATE': ['01/11/2025'] * n,
            'WATER_DEPTH': ['100'] * n, 'SURF_LATITUDE': ['28.0'] * n, 'SURF_LONGITUDE': ['-90.0'] * n}
    base.update(columns)
    return pd.DataFrame(base)


def test_actual_dates_and_full_year_filter():
    rows = borehole_rows(WELL_SPUD_DATE=['01/01/2025', '01/01/2025', '01/01/2026', 'bad'],
                         TOTAL_DEPTH_DATE=['01/11/2025', '01/01/2025', '01/02/2026', '01/01/2025'])
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
    monkeypatch.setattr(build.urllib.request, 'urlopen', lambda *a, **k: pytest.fail('Network access in offline test'))
    monkeypatch.setattr(build, 'fetch', lambda *a, **k: pytest.fail('Network access in offline test'))
    with pytest.raises(FileNotFoundError):
        build.cache_source(tmp_path, 'source.zip', 'https://example.org/source.zip', True)
    (tmp_path / 'source.zip').write_bytes(b'changed')
    (tmp_path / 'source.receipt.json').write_text(json.dumps({'url': 'https://example.org/source.zip', 'sha256': 'wrong'}))
    with pytest.raises(ValueError, match='receipt mismatch'):
        build.cache_source(tmp_path, 'source.zip', 'https://example.org/source.zip', True)


def test_issued_pin_rejects_self_consistent_substitute(tmp_path):
    p = tmp_path / 'source.zip'
    p.write_bytes(b'substitute')
    p.with_suffix('.receipt.json').write_text(json.dumps({'url': 'https://example.org/source.zip', 'sha256': build.sha(p)}))
    with pytest.raises(ValueError, match='issued source pin'):
        build.cache_source(tmp_path, p.name, 'https://example.org/source.zip', True, 'issued-digest')


def test_every_source_including_the_land_outline_is_pinned():
    pins = json.loads((ROOT / 'inputs' / 'source-pins.json').read_text(encoding='utf-8'))
    assert set(pins) == set(build.FILES)
    assert build.FILES[build.LAND].startswith('https://raw.githubusercontent.com/nvkelso/natural-earth-vector/' + build.NE_COMMIT)


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
    cells = Cells()
    cells.feed(re.search(r'<table>.*?</table>', raw_page(), re.S)[0])
    table = pd.read_csv(ROOT / 'data/table1.csv', dtype=str, keep_default_na=False)
    assert cells.rows == [list(table.columns)] + table.values.tolist()
    rig = pd.read_csv(ROOT / 'data/fig-p1-new-well-permits-by-rig-type.csv')
    depth = pd.read_csv(ROOT / 'data/new-well-permits-by-water-depth.csv')
    for i, category in enumerate(build.RIGS):
        assert int(table.iloc[i, 1].replace(',', '')) == rig[category].sum()
    for i, column in enumerate(build.WK):
        assert int(table.iloc[-1, i + 2].replace(',', '')) == depth[column].sum()


def test_r7_count_conservation_and_exact_pies():
    rig = pd.read_csv(ROOT / 'data/fig-p1-new-well-permits-by-rig-type.csv')
    depth = pd.read_csv(ROOT / 'data/new-well-permits-by-water-depth.csv')
    assert rig.total.sum() == 2895
    assert rig[build.RIGS].sum(axis=1).equals(rig.total)
    assert depth[build.WK].sum(axis=1).equals(depth.permits)
    assert rig.total.equals(depth.permits)
    for kind, frame, keys in [('rig', rig, build.RIGS), ('depth', depth, build.WK)]:
        pies = pd.read_csv(ROOT / f'data/pies-{kind}.csv')
        for year in [2005, 2015, 2025]:
            values = list(frame[frame.year.eq(year)][keys].iloc[0])
            assert list(pies[pies.year.eq(year)].permits) == values


def test_depth_statement_fails_closed_for_new_missing_depth():
    stats = pd.read_csv(ROOT / 'data/days-summary.csv')
    stats.loc[stats.band.eq('Missing depth'), 'records'] = 1
    with pytest.raises(ValueError, match='missing depth'):
        build.days_table(stats)


def test_observations_reject_a_missing_band_median(tmp_path):
    stats = pd.read_csv(ROOT / 'data/days-summary.csv')
    stats.loc[stats.activity.eq('Intervention') & stats.band.eq(build.BANDS[0]), 'median_days'] = float('nan')
    path = tmp_path / 'days.csv'
    stats.to_csv(path, index=False)
    with pytest.raises(ValueError, match='four depth bands'):
        build.day_observations(path)


# Owner comment 1: Deckhand opening graphic, map and hashtags ---------------------------------

def test_deckhand_opening_slot_is_marked_once_above_the_title_and_draws_nothing():
    page = rendered_prose()
    assert page.count('id="deckhand-opening"') == 1
    slot = page.split('id="deckhand-opening"')[1].split('</div>')[0]
    assert '<svg' not in slot and '<img' not in slot
    assert page.index('id="deckhand-opening"') < page.index('<h1>')


def test_map_wells_select_original_gulf_boreholes_in_both_periods():
    rows = borehole_rows(
        REGION_CODE=['G', 'G', 'P', 'G', 'G', 'G', 'G'],
        WELL_NAME_SUFFIX=['ST00BP00', 'ST00BP00', 'ST00BP00', 'ST01BP00', 'ST00BP00', 'ST00BP00', 'ST00BP00'],
        BOREHOLE_STAT_CD=['PA', 'PA', 'PA', 'PA', 'CNL', 'PA', 'PA'],
        WELL_SPUD_DATE=['01/01/2005', '06/01/2023', '01/01/2005', '01/01/2005', '01/01/2005', '01/01/2015', '01/01/2009'],
        WATER_DEPTH=['100', '6000', '100', '100', '100', '100', '2000'],
        SURF_LATITUDE=['28.0', '27.0', '28.0', '28.0', '28.0', '28.0', ''])
    wells, audit = build.map_wells(rows)
    # Rows 0 and 1 map; 2 is Pacific, 3 a sidetrack, 4 cancelled, 5 outside both periods, 6 has no latitude.
    assert list(wells.api_well_number) == ['0', '1']
    assert list(wells.band) == ['Under 100 m', '1,500 m and deeper']   # 6000 ft = 1,828.8 m
    assert audit.set_index('period').loc['2005 to 2009', 'missing_or_outside_coordinates'] == 1


def test_map_observation_matches_hand_counts_and_page():
    summary = pd.read_csv(ROOT / 'data/map-summary.csv').set_index('period')
    assert summary.total.tolist() == [1584, 246]
    sentence = build.map_observation(summary)
    # Hand check: 1,089 / 1,584 = 68.75 % and (209 + 160) / 1,584 = 23.30 %;
    # 33 / 246 = 13.41 % and (95 + 108) / 246 = 82.52 %.
    for value in ['68.8 %', '23.3 %', '13.4 %', '82.5 %', '1,584', '246']:
        assert value in sentence
    first_bullet = rendered_prose().split('Some of the observations are as follows:</p>')[1].split('</li>')[0]
    assert sentence in first_bullet and 'href="#fig-map">Figure 1</a>' in first_bullet


def test_land_rings_are_clamped_to_the_box_and_deduplicated(tmp_path):
    ring = [[-120, 30], [-90, 30], [-90, 30], [-90, 40], [-120, 40], [-120, 30]]
    far = [[10, 10], [11, 10], [11, 11], [10, 10]]
    path = tmp_path / 'land.geojson'
    path.write_text(json.dumps({'features': [{'geometry': {'type': 'Polygon', 'coordinates': [ring]}},
                                             {'geometry': {'type': 'Polygon', 'coordinates': [far]}}]}), encoding='utf-8')
    rings = build.land_rings(path)
    assert rings == [[(-101.0, 30), (-90, 30), (-90, 34.0), (-101.0, 34.0), (-101.0, 30)]]


def test_hashtag_line_closes_the_article_before_the_appendices():
    page = rendered_prose()
    line = re.findall(r'<p class="hashtags">(.*?)</p>', page)
    assert len(line) == 1
    tags = line[0].split()
    assert 5 <= len(tags) <= 10 and all(re.fullmatch(r'#[A-Za-z]+', t) for t in tags)
    assert {'#GulfOfAmerica', '#GulfOfMexico'} <= set(tags)
    assert page.index('Prepared: Analyst Deckhand') < page.index('class="hashtags"') < page.index('<h2 id="reusable-prompts">')


# Owner comments 2 to 6: short titles, numbered notes, shared pie titles ----------------------

def captions():
    return re.findall(r'<p class="ft">(.*?)</p>\s*<ol class="fn">(.*?)</ol>', rendered_prose(), re.S)


def test_every_figure_and_table_has_a_short_title_and_numbered_notes():
    found = captions()
    titles = [t for t, _ in found]
    assert [re.match(r'(Figure \d+|Table B?\d+) - ', t)[1] for t in titles] == [
        'Figure 1', 'Figure 2', 'Figure 3', 'Figure 4', 'Figure 5', 'Table 1', 'Figure 6', 'Table B1']
    for title, notes in found:
        assert len(title.split(' - ', 1)[1].split()) <= 10, title
        assert not re.search(r'Source|Data:|\.csv|retrieved', title)
        assert len(re.findall(r'<li>', notes)) >= 3
        assert re.search(r'Sources?:|as Figure \d', notes) and 'Data: ' in notes
    page = rendered_prose()
    assert page.count('<p class="ft">') == len(found)
    assert not re.search(r'Figure \d[a-e] -|<sup>a</sup>', page)


def test_each_pie_set_is_one_figure_with_one_legend_and_only_years_on_pies(tmp_path, monkeypatch):
    captured = {}
    def capture(fig, out, name):
        if name.startswith('pies-'):
            captured[name] = ([ax.get_title() for ax in fig.axes], len(fig.legends),
                              [t.get_text() for ax in fig.axes for t in ax.texts])
        build.plt.close(fig)
    monkeypatch.setattr(build, 'save_figure', capture)
    (tmp_path / 'data').mkdir()
    rig = pd.read_csv(ROOT / 'inputs/fig-p1-new-well-permits-by-rig-type.csv')
    depth = pd.read_csv(ROOT / 'inputs/new-well-permits-by-water-depth.csv')
    payload = build.count_figures(rig, depth, tmp_path)
    sets = [c for c in payload if c['kind'] == 'pieset']
    assert [c['id'] for c in sets] == ['pies-rig', 'pies-depth']
    for chart in sets:
        titles, legends, texts = captured[chart['id']]
        assert titles == ['2005', '2015', '2025'] and legends == 1
        for pie in chart['pies']:
            assert all(v > 0 for v in pie['values'])
            assert pie['shares'] == [f'{v / pie["total"] * 100:.1f}%' for v in pie['values']]
            for share in pie['shares']:   # every share is printed, inside or in the under-5 % list
                assert any(share in t for t in texts)
    rig2005 = sets[0]['pies'][0]
    assert rig2005['small'] == ['Under 5%:', 'Drillship 4.7%; DP semisubmersible 2.8%', 'Platform rig 3.1%; Other 0.9%']
    page = rendered_prose()
    assert 'Permits each year: 322 in 2005, 83 in 2015, 47 in 2025.' in page


def test_small_share_lines_group_two_per_line():
    assert build.small_share_lines(['A', 'B', 'C'], [96, 3, 1], ['96.0%', '3.0%', '1.0%'], 100) == ['Under 5%:', 'B 3.0%; C 1.0%']
    assert build.small_share_lines(['A'], [10], ['100.0%'], 10) == []


# Owner comment 7: interactive charts in the order of a well's life ---------------------------

def test_activities_follow_the_life_of_a_well():
    assert build.ACTIVITIES == ['Spud to total depth', 'Completion', 'Intervention',
                                'Temporary abandonment', 'Permanent abandonment']
    page = rendered_prose()
    labels = re.findall(r'<p class="stage-label">([a-e])\. (\w[\w ]*?) <span', page)
    assert labels == [('a', 'Drilling'), ('b', 'Completion'), ('c', 'Intervention'),
                      ('d', 'Temporary abandonment'), ('e', 'Permanent abandonment')]
    observations = page.split('<h3>3.1 ')[1].split('<h3>3.2 ')[0]
    order = [observations.index(w) for w in ['Drilling:', 'Completion:', 'Intervention:', 'Temporary abandonment:', 'Permanent abandonment:']]
    assert order == sorted(order)
    table = page.split('id="counting-rules"')[1]
    rows = [table.index(f'<td>{build.stage_name(a)}</td>') for a in build.ACTIVITIES]
    assert rows == sorted(rows)


def test_section3_observations_read_csv_and_match_page(tmp_path):
    stats = pd.read_csv(ROOT / 'data/days-summary.csv')
    def medians(activity):
        return stats[stats.activity.eq(activity) & stats.band.isin(build.BANDS)].median_days
    drilling, completion = medians('Spud to total depth'), medians('Completion')
    expected = [
        f'Drilling: recorded spud-to-total-depth medians rise with water depth, from {drilling.iloc[0]:g} d under 100 m to {drilling.iloc[-1]:g} d at 1,500 m and deeper.',
        f'Completion: estimate medians rise with water depth, from {completion.iloc[0]:g} d under 100 m to {completion.iloc[-1]:g} d at 1,500 m and deeper.',
    ] + [f'{a}: estimate medians range from {medians(a).min():g} to {medians(a).max():g} d across the four depth bands.'
         for a in ['Intervention', 'Temporary abandonment', 'Permanent abandonment']]
    # Hand check against Table B1: drilling 21 to 67 d; completion 10 to 40 d; temporary abandonment 5 to 14 d.
    assert 'from 21 d under 100 m to 67 d' in expected[0] and 'from 10 d under 100 m to 40 d' in expected[1]
    assert 'from 5 to 14 d' in expected[3]
    assert build.day_observations(ROOT / 'data/days-summary.csv') == expected
    section = rendered_prose().split('<h3>3.1 ')[1].split('<h3>3.2 ')[0]
    assert re.findall(r'<li>(.*?)</li>', section, re.S) == expected
    stats.loc[stats.activity.eq('Completion') & stats.band.eq(build.BANDS[0]), 'median_days'] = 11
    changed = tmp_path / 'days.csv'
    stats.to_csv(changed, index=False)
    assert 'from 11 d' in build.day_observations(changed)[1]


def test_every_chart_is_interactive_with_a_static_fallback():
    payload = chart_payload()
    ids = [c['id'] for c in payload]
    assert ids == build.IMAGES
    assert {c['kind'] for c in payload} == {'map', 'bar', 'pieset', 'interval'}
    page = rendered_prose()
    for chart_id in ids:
        assert page.count(f'<div id="{chart_id}" class="viz"') == 1
        assert page.count(f'data-for="{chart_id}" src="data:image/png;base64,') == 1
        assert (ROOT / 'figures' / f'{chart_id}.png').exists() and (ROOT / 'figures' / f'{chart_id}.svg').exists()
    stats = pd.read_csv(ROOT / 'data/days-summary.csv')
    drilling = next(c for c in payload if c['id'] == 'days-drilling')
    expected = stats[stats.activity.eq('Spud to total depth') & stats.band.isin(build.BANDS)]
    assert drilling['median'] == expected.median_days.tolist() and drilling['n'] == expected.n.tolist()
    page_raw = raw_page()
    assert "kinds={bar,pieset,map,interval}" in page_raw and "updatemenus" in page_raw
    assert '.viz{display:none}' in page_raw
    assert re.findall(r'<script src="([^"]+)"', page_raw) == ['https://cdn.plot.ly/plotly-2.35.2.min.js']


def test_map_payload_has_both_periods_and_every_mapped_well():
    chart = chart_payload()[0]
    wells = pd.read_csv(ROOT / 'data/map-wells.csv')
    assert chart['periods'] == ['2005 to 2009', '2021 to 2025']
    assert sum(len(t['lon']) for t in chart['traces']) == len(wells) == 1584 + 246
    assert len(chart['land']) > 10


# Page contract carried forward -----------------------------------------------------------------

def test_rendered_html_contract():
    page = rendered_prose()
    assert re.search(r'Some of the observations are as follows:</p>\s*<ul>', page)
    assert 'Appendix A Reusable prompts' in page
    headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', page)
    assert all(re.match(r'(\d+(\.\d+)? |B\.\d+ |Appendix [AB] )', h) or h in ('What you need to run this', 'Reproduce the published result', 'Adapt it to your project') for h in headings)
    assert '4 Outlook and open points' in headings and '3 Days from drilling to abandonment' in headings
    assert '<blockquote class="takeaway">' in page and 'class="toc"' in page and 'class="offer"' in page
    assert 'Table 2' not in page
    body = re.sub(r'data:image/png;base64,[^"]+', '', page.split('id="review-panel"')[1].split('</div>', 1)[1])
    assert not re.search(r'\br[0-9]\b|receipt|snapshot|b26eb928', body.replace('build_r9.py', '').replace('issue2_public_data_r9', ''))
    assert not re.search(r'[A-Z]:[\\/]|file://|/mnt/|/Users/', page)
    assert not re.search(r'\b(acceptable|conservative|safe)\b', page, re.I)
    assert '—' not in body
    assert page.count('Our hypothesis:') == 2
    assert 'The year 2026 runs only to the file of 2 November 2026.' in page
    assert 'EST_OPERATION_DAYS' in page and 'TOTAL_DEPTH_DATE' in page


def test_body_rules_are_short_and_details_are_in_appendix_b():
    page = rendered_prose()
    rules = page.split('<h3>3.2 ')[1].split('<h3>3.3 ')[0]
    bullets = re.findall(r'<li>(.*?)</li>', rules, re.S)
    assert len(bullets) == 5 and bullets[0].startswith('Drilling days')
    assert all(len(re.sub('<[^>]+>', '', b).split()) <= 30 for b in bullets)
    assert rules.count('href="#counting-rules"') == 1
    body, appendix = page.split('<h2 id="counting-rules">')
    for detail in ['SN_APM', 'ZONE', 'PERMABAN', 'PLUGBACK', 'REGION_CODE', 'ST00BP00', 'SURF_LATITUDE', 'Selection counts before day exclusions', 'repeat-key sensitivity check']:
        assert detail not in body.split('<h2 id="s3">3 ')[1].split('<h2 id="reusable-prompts">')[0]
        assert detail in appendix
    assert page.index('Appendix A Reusable prompts') < page.index('Appendix B Counting rules and record counts for section 3')


def test_body_holds_figure_6_and_table_1_and_appendix_holds_full_audit():
    page = rendered_prose()
    body, appendix = page.split('<h2 id="counting-rules">')
    assert len(re.findall(r'<table>.*?</table>', body, re.S)) == 1
    assert 'Figure 6 -' in body
    assert 'Missing/invalid (-)' in appendix and 'Nonpositive (-)' in appendix and 'Missing depth' in appendix


def test_outlook_section_holds_hypotheses_open_points_and_closing_order():
    page = rendered_prose()
    section = page.split('<h2 id="s4">')[1].split('<h2 id="reusable-prompts">')[0]
    assert section.count('Our hypothesis:') == 2
    assert '(Figure 2), jack-up work' in section and '(Figure 4), new-well engineering' in section
    assert 'To try it out or adapt the analysis, see <a href="#reusable-prompts">reusable prompt</a>.' in section
    assert section.index('Our hypothesis:') < section.index('Open points') < section.index('class="offer"') < section.index('If you have run your own analysis')
    assert 'support@aceengineer.com' not in section.split('class="offer"')[1].split('</div>')[0]
    assert page.count('are not paired') == 1
    for part in ['What you need to run this', 'Reproduce the published result', 'Adapt it to your project']:
        assert page.count('<h3>' + part + '</h3>') == 1
    appendix = page.split('<h2 id="reusable-prompts">')[1].split('<h2 id="counting-rules">')[0]
    assert 'SHA-256' in appendix and 'file of 12 November 2026' in appendix and 'Natural Earth' in appendix
    assert 'Mapped wells: 1,584 (2005 to 2009) and 246 (2021 to 2025).' in appendix
    assert 'issue2_public_data_r9/build_r9.py' in appendix
    assert appendix.rstrip().endswith('write to support@aceengineer.com.</p>')


def test_page_dates_and_source_lines():
    page = rendered_prose()
    assert not re.search(r'\d{4}-\d{2}-\d{2}|\(UTC\)', re.sub(r'<style.*?</style>', '', page, flags=re.S))
    source = 'Source: BSEE Application for Permit to Drill raw data (<a href="https://www.data.bsee.gov/Well/Files/APDRawData.zip">APDRawData.zip</a>), file of 2 November 2026, retrieved 3 November 2026.'
    assert page.count(source) == 3   # Figures 2 and 4 and Table 1; the pie sets point to them
    assert page.count('file of 12 November 2026, retrieved 13 November 2026') >= 3
    assert not (ROOT / 'review-plan.html').exists()


# Review-gate round 1 fixes ---------------------------------------------------------------------

def test_archive_date_is_the_newest_data_member_stamp(tmp_path):
    import zipfile
    path = tmp_path / 'a.zip'
    with zipfile.ZipFile(path, 'w') as z:
        z.writestr(zipfile.ZipInfo('a/old.txt', (2026, 11, 2, 1, 0, 0)), 'x')
        z.writestr(zipfile.ZipInfo('a/new.txt', (2026, 11, 12, 23, 0, 0)), 'y')
        z.writestr(zipfile.ZipInfo('a/readme.pdf', (2026, 12, 1, 0, 0, 0)), 'z')
    assert build.archive_date(path) == '2026-11-12'


def test_sources_record_file_dates_and_roles_used_on_the_page():
    sources = pd.read_csv(ROOT / 'data/sources.csv', keep_default_na=False).set_index('file')
    assert sources.loc['BoreholeRawData.zip', 'file_date'] == '2026-11-12'
    assert sources.loc['eWellAPMRawData.zip', 'file_date'] == '2026-11-12'
    assert sources.loc['APDRawData.zip (file of 2 November 2026)', 'file_date'] == '2026-11-02'
    assert sources.loc['eWellAPMRawData.zip', 'role'] == 'Duration analysis'
    assert sources.loc['BoreholeRawData.zip', 'role'] == 'Duration analysis and map'
    assert '12 November 2026' not in (ROOT / 'build_r9.py').read_text(encoding='utf-8')
    assert '12 November 2026' not in (ROOT / 'inputs/page-template.html').read_text(encoding='utf-8')
    assert rendered_prose().count('file of 12 November 2026') >= 7


def test_hover_values_use_the_table_rounding():
    payload = {c['id']: c for c in chart_payload()}
    # Table B1 shows Q3 115.25 d as 115.2 (four significant figures); the hover must show the same text.
    assert payload['days-drilling']['shown'][2] == ['30', '55.5', '115.2']
    assert 'c.shown[i][1]' in raw_page() and 'toPrecision(4)' not in raw_page().split('const charts=')[1]


def test_map_counts_note_labels_each_band():
    note = re.search(r'<li>Counts: (.*?)</li>', rendered_prose())[1]
    assert note.startswith('2005 to 2009: 1,584 wells (under 100 m: 1,089; 100 to 500 m: 126; 500 to 1,500 m: 209; 1,500 m and deeper: 160)')


# Review-gate round 2 fixes (second-provider review at aa9e55aa) -------------------------------

PLOTLY_SHA256 = '6d21266ce1bd7d9e5ab4e115989c70c20de0382fd973a8f26ab58619eba4d603'
# Sub-resource integrity of the same pinned bytes (SHA-384, base64), recorded when the pin was checked.
PLOTLY_SRI = 'sha384-cCVCZkAjYNxaYKbM8lsArLznDF/SvMFr1jcZrvOpSTCa0W40ZAdLzHCEulnUa5i7'
# FIPS 180-2 test vector: SHA-384 of b'abc', in base64.
ABC_SRI = 'sha384-ywB1P0WjXou1oD1pmsZQBycsMqsO3tFjGotgWkP/W+2AhgcroefMI1i67KE0yCWn'


def test_tracked_page_is_under_the_unchanged_commit_size_limit():
    config = (ROOT.parents[2] / '.pre-commit-config.yaml').read_text(encoding='utf-8')
    maxkb = int(re.search(r'id: check-added-large-files\s+args: \[--maxkb=(\d+)\]', config)[1])
    assert build.SIZE_LIMIT == maxkb * 1024 == 1_024_000
    assert PAGE_FILE.stat().st_size < build.SIZE_LIMIT


def test_page_writer_refuses_oversized_pages_and_bundles_inside_the_example(tmp_path):
    cache, out = tmp_path / 'cache', tmp_path / 'out'
    cache.mkdir()
    out.mkdir()
    (cache / build.PLOTLY).write_bytes(b'abc')
    with pytest.raises(ValueError, match='commit limit'):
        build.write_pages(out, cache, '@@PLOTLY_SCRIPT@@' + 'x' * build.SIZE_LIMIT)
    assert not (out / build.PAGE).exists()
    with pytest.raises(ValueError, match='Unresolved page token'):
        build.write_pages(out, cache, '@@PLOTLY_SCRIPT@@@@CHART_DATA@@')
    inside = build.ROOT / 'bundle-test.html'
    with pytest.raises(ValueError, match='outside the tracked example folder'):
        build.write_pages(out, cache, '<p>page</p>@@PLOTLY_SCRIPT@@', bundle=inside)
    assert not inside.exists()
    bundle = tmp_path / 'offline' / 'page.html'
    build.write_pages(out, cache, '<p>page</p>@@PLOTLY_SCRIPT@@', bundle=bundle)
    assert (out / build.PAGE).read_text(encoding='utf-8') == (
        '<p>page</p><script src="https://cdn.plot.ly/plotly-2.35.2.min.js" '
        f'integrity="{ABC_SRI}" crossorigin="anonymous"></script>')
    assert bundle.read_text(encoding='utf-8') == '<p>page</p><script>abc</script>'


def test_page_loads_the_pinned_plotly_release_with_integrity_and_keeps_static_fallbacks():
    raw = PAGE_FILE.read_text(encoding='utf-8')
    assert re.findall(r'<script\b[^>]*>', raw) == [
        f'<script src="https://cdn.plot.ly/plotly-2.35.2.min.js" integrity="{PLOTLY_SRI}" crossorigin="anonymous">',
        '<script>']
    assert 'plotly.js v2.35.2' not in raw
    pins = json.loads((ROOT / 'inputs/source-pins.json').read_text(encoding='utf-8'))
    assert pins[build.PLOTLY] == PLOTLY_SHA256
    assert build.FILES[build.PLOTLY] == 'https://cdn.plot.ly/plotly-2.35.2.min.js'
    assert chart_script().lstrip().startswith("(function(){\nif(typeof Plotly==='undefined')return;\n")
    cached = ROOT / 'cache' / build.PLOTLY
    if cached.exists() and hashlib.sha256(cached.read_bytes()).hexdigest() == PLOTLY_SHA256:
        assert f'integrity="{PLOTLY_SRI}"' in build.plotly_script(ROOT / 'cache')


def test_without_plotly_the_charts_stay_static():
    ran = run_chart_script(chart_script(), plotly=False)
    assert ran['plots'] == [] and ran['touched'] == []


@pytest.mark.parametrize('url', ['http://www.data.bsee.gov/Well/Files/APDRawData.zip', 'file:///C:/Windows/win.ini',
                                 'ftp://example.org/a.zip', 'data:text/plain,abc',
                                 'www.data.bsee.gov/Well/Files/APDRawData.zip'])
def test_downloads_accept_https_only(url, monkeypatch):
    monkeypatch.setattr(build, 'https_opener', lambda: pytest.fail('opener built for a refused address'))
    with pytest.raises(ValueError, match='Only https downloads'):
        build.fetch(url)


def test_https_opener_has_no_file_ftp_data_or_plain_http_handler():
    handlers = build.https_opener().handlers
    assert any(type(h) is urllib.request.HTTPSHandler for h in handlers)
    banned = (urllib.request.HTTPHandler, urllib.request.FileHandler, urllib.request.FTPHandler,
              urllib.request.DataHandler, urllib.request.UnknownHandler, urllib.request.ProxyHandler)
    assert not [h for h in handlers if isinstance(h, banned)]
    assert 'urlopen(' not in (ROOT / BUILD_FILE).read_text(encoding='utf-8')


def test_redirects_are_followed_only_to_https():
    handler = build.HttpsOnlyRedirect()
    request = urllib.request.Request('https://www.data.bsee.gov/Well/Files/APDRawData.zip')
    with pytest.raises(ValueError, match='Only https downloads'):
        handler.redirect_request(request, None, 302, 'Found', {}, 'http://www.data.bsee.gov/Well/Files/APDRawData.zip')
    moved = handler.redirect_request(request, None, 302, 'Found', {}, 'https://mirror.example.org/APDRawData.zip')
    assert moved.full_url == 'https://mirror.example.org/APDRawData.zip'


def test_foot_to_metre_factor_is_the_exact_international_foot():
    # Independent of the build constant: 1 ft = 12 in and 1 in = 25.4 mm exactly.
    assert Fraction(str(build.FT_TO_M)) == 12 * Fraction('0.0254') == Fraction(3048, 10000)
    source = (ROOT / BUILD_FILE).read_text(encoding='utf-8')
    assert 'NIST Special Publication 811' in source and 'nist-guide-si-appendix-b8' in source
    code = '\n'.join(line for line in source.splitlines() if not line.lstrip().startswith('#'))
    assert re.findall(r'.*\.3048.*', code) == ['FT_TO_M = 0.3048']


@pytest.mark.parametrize('feet,index', [
    # Metres worked by hand as feet x 12 in x 25.4 mm: 328.08 ft = 99.998784 m, 328.09 ft = 100.001832 m,
    # 1,640.41 ft = 499.996968 m, 1,640.42 ft = 500.000016 m, 4,921.25 ft = 1,499.997 m,
    # 4,921.26 ft = 1,500.000048 m.
    (328.08, 0), (328.09, 1), (1640.41, 1), (1640.42, 2), (4921.25, 2), (4921.26, 3)])
def test_band_edges_from_hand_worked_feet(feet, index):
    assert build.band_from_feet(feet) == build.BANDS[index]


def test_page_cites_the_conversion_definition():
    page = rendered_prose()
    assert page.count('1 ft = 0.3048 m exactly') == 2
    assert page.count('nist-guide-si-appendix-b8">NIST SP 811, Appendix B.8</a>') == 1
    assert page.count('(NIST SP 811, Appendix B.8)') == 1


@pytest.mark.parametrize('value', [None, '', 'dashwork/issue2-public-data-r8', 'HEAD', 'aa9e55aa',
                                   'aa9e55aa91427a54002caec8ba9dcf0fe6953d2',
                                   'AA9E55AA91427A54002CAEC8BA9DCF0FE6953D20',
                                   'aa9e55aa91427a54002caec8ba9dcf0fe6953d20\n'])
def test_rebuild_citation_needs_a_full_commit_sha(value):
    with pytest.raises(ValueError, match='full 40-character SHA'):
        build.check_build_commit(value)


def test_build_refuses_a_missing_or_branch_build_commit_before_writing(tmp_path):
    for argv in ([], ['--build-commit', 'dashwork/issue2-public-data-r8']):
        with pytest.raises(SystemExit) as stop:
            build.main(['--offline', '--data-dir', str(tmp_path / 'cache'), '--output-dir', str(tmp_path / 'out')] + argv)
        assert stop.value.code == 2
    assert list(tmp_path.iterdir()) == []
    sha = 'aa9e55aa91427a54002caec8ba9dcf0fe6953d20'
    assert build.check_build_commit(sha) == sha


def test_appendix_links_the_script_at_a_full_commit_sha():
    raw = PAGE_FILE.read_text(encoding='utf-8')
    links = re.findall(r'href="https://github\.com/vamseeachanta/worldenergydata/blob/([^/"]+)/examples/bsee/'
                       + re.escape(FOLDER) + '/' + re.escape(BUILD_FILE) + '"', raw)
    assert len(links) == 1 and re.fullmatch(r'[0-9a-f]{40}', links[0])
    assert f'at commit {links[0][:8]} of worldenergydata' in rendered_prose()
    readme = (ROOT / 'README.md').read_text(encoding='utf-8')
    assert readme.count('--build-commit "$(git rev-parse HEAD)"') == 2


def test_retained_inputs_match_the_manifest_and_text_files_use_lf():
    build.validate_inputs()
    text = [p for p in ROOT.rglob('*') if p.is_file() and not {'cache', '__pycache__'} & set(p.relative_to(ROOT).parts)
            and p.suffix in {'.json', '.csv', '.md', '.py', '.html', '.svg', '.txt'}]
    assert ROOT / 'inputs' / 'manifest.json' in text
    assert [p.relative_to(ROOT).as_posix() for p in text if b'\r' in p.read_bytes()] == []


def test_pie_legend_clicks_cannot_hide_slices():
    ran = run_chart_script(chart_script())
    pies = [p for p in ran['plots'] if p['traces'][0]['type'] == 'pie']
    assert [p['id'] for p in pies] == ['pies-rig', 'pies-depth']
    for pie in pies:
        assert pie['layout']['legend']['itemclick'] is False and pie['layout']['legend']['itemdoubleclick'] is False
        for trace in pie['traces']:
            assert re.fullmatch(r'%\{label\}<br>%\{value\} of \d+ permits \(%\{customdata\}\)<extra>\d{4}</extra>',
                                trace['hovertemplate'])


def test_map_period_buttons_keep_the_legend_band_selection():
    chart = chart_payload()[0]
    bands, fixed = chart['bands'], 1 + len(chart['bands'])
    legend = {b: 1 + i for i, b in enumerate(bands)}

    def expected(period, hidden):
        dummies = ['legendonly' if b in hidden else True for b in bands]
        return [True] + dummies + [False if t['axis'] != period else 'legendonly' if t['band'] in hidden else True
                                   for t in chart['traces']]

    def double(band):
        # Plotly 2.35.2 fires plotly_legendclick on both clicks, then plotly_legenddoubleclick.
        n = legend[band]
        return [['fig-map', 'plotly_legendclick', {'curveNumber': n}]] * 2 + [
            ['fig-map', 'plotly_legenddoubleclick', {'curveNumber': n}]]

    events = ([['fig-map', 'plotly_legendclick', {'curveNumber': legend[bands[0]]}],
               ['fig-map', 'plotly_buttonclicked', {'active': 1}],
               ['fig-map', 'plotly_buttonclicked', {'active': 0}]]
              + double(bands[2]) + [['fig-map', 'plotly_buttonclicked', {'active': 1}]] + double(bands[2]))
    ran = run_chart_script(chart_script(), events)
    plot = next(p for p in ran['plots'] if p['id'] == 'fig-map')
    assert [t.get('meta') for t in plot['traces'][fixed:]] == [t['axis'] for t in chart['traces']]
    assert [b['method'] for b in plot['layout']['updatemenus'][0]['buttons']] == ['skip', 'skip']
    assert ran['results'] == [False, None, None, False, False, False, None, False, False, False]
    seen = [r['visible'] for r in ran['restyles'] if r['id'] == 'fig-map']
    others = set(bands) - {bands[2]}
    assert seen == [
        expected(0, {bands[0]}),       # legend click hides the shallowest band
        expected(1, {bands[0]}),       # the period switch keeps it hidden
        expected(0, {bands[0]}),
        expected(0, {bands[0], bands[2]}), expected(0, {bands[0]}), expected(0, others),   # double click isolates one band
        expected(1, others),           # and the isolation holds in the other period
        expected(1, set(bands)), expected(1, others), expected(1, set()),   # a second double click shows all
    ]
