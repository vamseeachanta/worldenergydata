"""Offline regression cases for the newsletter's counting contract."""
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
spec = importlib.util.spec_from_file_location('build_r8', ROOT / 'build_r8.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
FOLDER = 'issue2_public_data_r8'
BUILD_FILE = 'build_r8.py'
PAGE_FILE = ROOT / 'issue2-public-data-r8.html'

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
    monkeypatch.setattr(build, 'fetch', lambda *a, **k: pytest.fail('Network access in offline test'))
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


def test_rendered_html_contract():
    page = (ROOT / 'issue2-public-data-r8.html').read_text(encoding='utf-8')
    page = re.sub(r'<script\b[^>]*>.*?</script>', '', page, flags=re.S)
    assert 'Some of the observations are as follows:' in page
    assert re.search(r'Some of the observations are as follows:</p>\s*<ul>', page)
    assert 'Appendix A Reusable prompts' in page
    headings = re.findall(r'<h[23][^>]*>(.*?)</h[23]>', page)
    assert all(re.match(r'(\d+(\.\d+)? |B\.\d+ |Appendix [AB] )', h) or h in ('What you need to run this', 'Reproduce the published result', 'Adapt it to your project') for h in headings)
    assert '4 Outlook and open points' in headings
    assert '<blockquote class="takeaway">' in page and 'class="toc"' in page and 'class="offer"' in page
    assert 'Table 2' not in page
    assert not re.search(r'r7|r8|receipt|snapshot|-r7\.csv|b26eb928', page)
    assert '<sup>a</sup>' in page and 'a. The counts here are from the file of 2 November 2026.' in page
    assert not re.search(r'[A-Z]:[\\/]|file://|/mnt/|/Users/', page)
    assert not re.search(r'\b(acceptable|conservative|safe)\b', page, re.I)
    assert page.count('Our hypothesis:') == 2
    assert 'The year 2026 runs only to the file of 2 November 2026.' in page
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
        assert detail not in body.split('<h2 id="s3">3 ')[1].split('<h2 id="reusable-prompts">')[0]
        assert detail in appendix
    assert page.index('Appendix A Reusable prompts') < page.index('Appendix B Counting rules and record counts for section 3')


def test_body_holds_figure_3_and_table_1_and_appendix_holds_full_audit():
    page = rendered_prose()
    body, appendix = page.split('<h2 id="counting-rules">')
    assert len(re.findall(r'<table>.*?</table>', body, re.S)) == 1
    assert 'Table 2' not in page
    assert 'Figure 3 -' in body
    assert 'Missing/invalid (-)' in appendix and 'Nonpositive (-)' in appendix
    assert 'Missing depth' in appendix


def test_outlook_section_holds_hypotheses_open_points_and_closing_order():
    page = rendered_prose()
    section = page.split('<h2 id="s4">')[1].split('<h2 id="reusable-prompts">')[0]
    assert section.count('Our hypothesis:') == 2
    assert 'To try it out or adapt the analysis, see <a href="#reusable-prompts">reusable prompt</a>.' in section
    assert section.index('Our hypothesis:') < section.index('Open points') < section.index('class="offer"') < section.index('If you have run your own analysis')
    assert 'support@aceengineer.com' not in section.split('class="offer"')[1].split('</div>')[0]
    assert page.index('Figure 3 -') < page.index('<h2 id="s4">')
    for part in ['What you need to run this', 'Reproduce the published result', 'Adapt it to your project']:
        assert page.count('<h3>' + part + '</h3>') == 1
    appendix = page.split('<h2 id="reusable-prompts">')[1].split('<h2 id="counting-rules">')[0]
    assert 'SHA-256' in appendix and 'file of 12 November 2026' in appendix
    assert appendix.rstrip().endswith('write to support@aceengineer.com.</p>')


def test_page_dates_captions_and_minimal_review_marker():
    page = rendered_prose()
    assert not re.search(r'\d{4}-\d{2}-\d{2}|\(UTC\)', re.sub(r'<style.*?</style>', '', page, flags=re.S))
    source = 'Source: BSEE Application for Permit to Drill raw data (<a href="https://www.data.bsee.gov/Well/Files/APDRawData.zip">APDRawData.zip</a>), file of 2 November 2026, retrieved 3 November 2026. Data:'
    assert page.count(source) == 2
    assert page.count('types with no permits that year are not shown.') == 3
    assert page.count('bands with no permits that year are not shown.') == 3
    assert 'not statistical medians' not in page
    panel = page.split('<div class="review-panel"')[1].split('</div>')[0]
    assert 'Review copy' in panel
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
    depth = pd.read_csv(ROOT / 'inputs/new-well-permits-by-water-depth.csv')
    payload = build.count_figures(rig, depth, tmp_path)
    for chart in payload:
        if chart['kind'] != 'pie':
            continue
        assert all(v > 0 for v in chart['values'])
        assert chart['shares'] == [f'{v / chart["total"] * 100:.1f}%' for v in chart['values']]
        legends, labels = captured[chart['id']]
        assert legends == [f'{label}: {share}' for label, share in zip(chart['labels'], chart['shares'])]
        assert labels == [x for x, v in zip(chart['shares'], chart['values']) if v / chart['total'] * 100 >= 5]


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


def test_byline_at_foot_limits_once_and_plotly_blanks_small_slices():
    page = rendered_prose()
    byline = page.index('Prepared: Analyst Deckhand')
    assert page.index('If you have run your own analysis') < byline < page.index('<h2 id="reusable-prompts">')
    for phrase in ['not active drilling time', 'not a measured job duration', 'These are not unique jobs',
                   'present-day job durations', 'status-date basis used in the prior']:
        assert phrase not in page
    assert page.count('are not paired') == 1
    raw = (ROOT / 'issue2-public-data-r8.html').read_text(encoding='utf-8')
    assert "c.values[i]/c.total*100>=5?s:''" in raw
    assert 'SHA-256 <code>8f5ce969' in page and 'file of 12 November 2026' in page.split('Table B1 -')[1].split('</p>')[0]


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
    assert [p['id'] for p in pies] == [f'pie-{k}-{y}' for k in ['rig', 'depth'] for y in [2005, 2015, 2025]]
    for pie in pies:
        assert pie['layout']['legend']['itemclick'] is False and pie['layout']['legend']['itemdoubleclick'] is False
        # Shares in the labels are fixed text against the year total, so every slice must stay drawn.
        assert all(label.rsplit(': ', 1)[1].endswith('%') for label in pie['traces'][0]['labels'])
    bars = [p for p in ran['plots'] if p['traces'][0]['type'] == 'bar']
    assert len(bars) == 2 and all('itemclick' not in p['layout']['legend'] for p in bars)
