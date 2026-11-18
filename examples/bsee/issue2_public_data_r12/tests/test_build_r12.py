"""Offline checks of the revision 12 page: the Figure 1b axis colour and line-style notes, legend titles and
labelled key points generated from the data; and, as in revision 11: permit counts unchanged from revision 9,
Figure 1 windows and rolling averages traced to the borehole and WTI files, section 3 moved out, short appendices
with their full text in the repository, the revision 10 water-depth palette, notes before every title, and a
working chart script."""
import hashlib
import importlib.util
import json
import math
import re
import shutil
import subprocess
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
R9 = ROOT.parent / 'issue2_public_data_r9'
R10 = ROOT.parent / 'issue2_public_data_r10'
PAGE_FILE = ROOT / 'issue2-public-data-r12.html'
spec = importlib.util.spec_from_file_location('build_r12', ROOT / 'build_r12.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)
spec = importlib.util.spec_from_file_location('derive_r12', ROOT / 'derive_r12.py')
derive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(derive)


def page():
    return PAGE_FILE.read_text(encoding='utf-8')


def chart_data():
    return json.loads(re.search(r'const charts=(\[.*?\]);\n', page(), re.S).group(1))


def charts():
    return {c['id']: c for c in chart_data()}


# ---- permit counts stay those of revision 9 ----------------------------------------------------------------------

def test_every_input_matches_its_pin():
    build.validate_inputs()


def test_reused_data_files_are_byte_identical_to_revision_9():
    for name in build.REUSED:
        assert (ROOT / 'data' / (name + '.csv')).read_bytes() == (R9 / 'data' / (name + '.csv')).read_bytes(), name


@pytest.mark.parametrize('name', ['pies-rig', 'pies-depth'])
def test_regenerated_pie_shares_equal_revision_9(name):
    assert (ROOT / 'data' / (name + '.csv')).read_bytes() == (R9 / 'data' / (name + '.csv')).read_bytes()


def test_permit_check_values_are_unchanged():
    old = (R10 / 'issue2-public-data-r10.html').read_text(encoding='utf-8')
    pattern = r'From 2005 to 2026, [\d,]+ wells are counted this way'
    assert re.search(pattern, page()).group(0) == re.search(pattern, old).group(0)
    prompts = re.sub(r'\s+', ' ', (ROOT / 'prompts' / 'README.md').read_text(encoding='utf-8'))
    old_check = re.search(r'Check values: (2,895 wells); (band totals [^.]*?\(1,500 m and deeper\))', old)
    assert old_check
    assert f'Check values: {old_check.group(1)} with permits; {old_check.group(2)}' in prompts


# ---- Figure 1: windows, yearly wells, rolling averages and the oil price ------------------------------------------

def test_yearly_wells_reproduce_the_revision_9_map_well_for_well():
    wells = pd.read_csv(ROOT / 'data' / 'map-wells-by-year.csv', dtype={'api_well_number': str})
    derive.check_against_r9(wells)
    counts = pd.read_csv(ROOT / 'data' / 'new-wells-by-year.csv')
    assert counts.year.tolist() == build.YEARS
    assert counts[build.BANDS].sum(axis=1).tolist() == counts.total.tolist()
    assert int(counts.total.sum()) == len(wells)


def test_every_window_is_the_sum_of_its_years_and_matches_the_map_summary():
    counts = pd.read_csv(ROOT / 'data' / 'new-wells-by-year.csv')
    windows = pd.read_csv(ROOT / 'data' / 'map-windows.csv')
    assert list(zip(windows.start, windows.end)) == [(y - 4, y) for y in range(2009, 2026)]
    for row in windows.itertuples():
        assert row.total == counts[counts.year.between(row.start, row.end)].total.sum()
    summary = pd.read_csv(ROOT / 'data' / 'map-summary.csv').set_index('period')
    for (a, b), total in [((2005, 2009), 1584), ((2021, 2025), 246)]:
        assert windows[(windows.start == a) & (windows.end == b)].total.item() == total == summary.loc[f'{a} to {b}', 'total']
    frames = charts()['fig-map']['frames']
    assert [f['label'] for f in frames][0] == '2005 to 2009: 1,584 new wells'
    assert [sum(f['counts']) for f in frames] == windows.total.tolist()


def test_rolling_average_and_wti_hand_checks():
    trend = pd.read_csv(ROOT / 'data' / 'new-wells-trend.csv').set_index('year')
    # hand check: under 100 m, 2012 to 2014 = (62 + 60 + 64) / 3 = 62.0; 2015 to 2017 = (16 + 9 + 12) / 3 = 12.33
    assert trend.loc[2014, 'Under 100 m (3-year mean)'] == 62.0
    assert trend.loc[2017, 'Under 100 m (3-year mean)'] == 12.33
    assert trend.loc[[2005, 2006], 'total (3-year mean)'].isna().all()
    monthly = pd.read_csv(ROOT.parents[2] / 'data' / 'wti-monthly.csv')
    year = monthly[monthly.Date.str.startswith('2014')]
    assert len(year) == 12 and round(year.Price.mean(), 2) == trend.loc[2014, 'WTI (USD/bbl)'] == 93.26
    chart = charts()['fig-map-trend']
    assert chart['wti'] == trend['WTI (USD/bbl)'].tolist()
    assert chart['means'][0][9] == 62.0 and chart['means'][0][0] is None


def test_rolling_average_observation_reads_as_built():
    text = ('When the WTI oil price fell from USD 93.26 a barrel in 2014 to USD 48.69 in 2015 (annual means), the three-year '
            'average of new wells in less than 100 m of water fell from about 62 a year (2012 to 2014) to about 12 (2015 to 2017); '
            'in 500 m or more it fell from about 76 to about 59 (<a href="#fig-map-trend">Figure 1b</a>).')
    assert '<li>' + text + '</li>' in page()
    exact = ('Section 1 reads these three-year averages, new wells a year: under 100 m, 62.0 (2012 to 2014) and 12.3 '
             '(2015 to 2017); 500 m or more, 75.7 and 59.3.</li>')
    assert exact in page()


def test_oil_price_source_is_cited():
    text = page()
    assert 'US Energy Information Administration' in text
    assert f'blob/{build.WTI_COMMIT}/data/wti-monthly.csv' in text


# ---- one water-depth palette, validated ---------------------------------------------------------------------------

MACHADO = {
    'protan': [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
    'deutan': [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
    'tritan': [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]],
}


def lab(colour, kind=None):
    rgb = np.array([int(colour.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4)])
    rgb = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    if kind:
        rgb = np.array(MACHADO[kind]) @ rgb
    xyz = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]) @ np.clip(rgb, 0, 1)
    xyz = xyz / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


def ciede2000(c1, c2):
    (L1, a1, b1), (L2, a2, b2) = c1, c2
    cb = (math.hypot(a1, b1) + math.hypot(a2, b2)) / 2
    g = 0.5 * (1 - math.sqrt(cb ** 7 / (cb ** 7 + 25 ** 7)))
    a1, a2 = (1 + g) * a1, (1 + g) * a2
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2)
    h1, h2 = math.degrees(math.atan2(b1, a1)) % 360, math.degrees(math.atan2(b2, a2)) % 360
    dh = 0 if C1 * C2 == 0 else (h2 - h1 - 360 if h2 - h1 > 180 else h2 - h1 + 360 if h2 - h1 < -180 else h2 - h1)
    dH = 2 * math.sqrt(C1 * C2) * math.sin(math.radians(dh / 2))
    Lb, Cb = (L1 + L2) / 2, (C1 + C2) / 2
    hb = h1 + h2 if C1 * C2 == 0 else (h1 + h2) / 2 if abs(h1 - h2) <= 180 else (h1 + h2 + 360) / 2 if h1 + h2 < 360 else (h1 + h2 - 360) / 2
    T = (1 - 0.17 * math.cos(math.radians(hb - 30)) + 0.24 * math.cos(math.radians(2 * hb))
         + 0.32 * math.cos(math.radians(3 * hb + 6)) - 0.20 * math.cos(math.radians(4 * hb - 63)))
    Rt = -math.sin(math.radians(60 * math.exp(-((hb - 275) / 25) ** 2))) * 2 * math.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lb - 50) ** 2 / math.sqrt(20 + (Lb - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cb, 1 + 0.015 * Cb * T
    return math.sqrt(((L2 - L1) / Sl) ** 2 + ((C2 - C1) / Sc) ** 2 + (dH / Sh) ** 2 + Rt * ((C2 - C1) / Sc) * (dH / Sh))


def test_ciede2000_matches_a_published_pair():
    # Sharma, Wu and Dalal (2005), test pair 1: (50, 2.6772, -79.7751) and (50, 0, -82.7485) give 2.0425
    assert ciede2000((50, 2.6772, -79.7751), (50, 0, -82.7485)) == pytest.approx(2.0425, abs=1e-4)


@pytest.mark.parametrize('kind', [None, 'protan', 'deutan', 'tritan'])
def test_depth_palette_reads_darker_for_deeper_and_stays_apart(kind):
    labs = [lab(c, kind) for c in build.WC]
    lightness = [l[0] for l in labs]
    assert all(a > b for a, b in zip(lightness, lightness[1:])), lightness
    gaps = [ciede2000(labs[i], labs[j]) for i in range(4) for j in range(i + 1, 4)]
    assert min(gaps) >= 15, gaps


def test_depth_palette_is_from_the_rig_type_family():
    okabe_ito = {'#E69F00', '#56B4E9', '#009E73', '#F0E442', '#0072B2', '#D55E00', '#CC79A7'}
    brand = {'#0b3d5c', '#2BB2A6'}
    assert set(build.WC) <= okabe_ito | brand
    assert set(build.RC[:6]) <= okabe_ito | brand


def test_one_depth_palette_in_every_depth_chart():
    found = charts()
    assert found['fig-depth']['colours'] == build.WC
    assert found['fig-map-trend']['colours'] == build.WC
    assert all(set(p['colours']) <= set(build.WC) for p in found['pies-depth']['pies'])
    assert [t['colour'] for t in found['fig-map']['traces']] == build.WC
    assert build.OIL not in build.WC


def test_slice_labels_use_dark_ink_on_light_fills():
    assert build.ink_on('#F0E442') == build.INK
    assert build.ink_on('#0b3d5c') == '#ffffff'


# ---- section 3 moved, appendices short -----------------------------------------------------------------------------

def test_section_3_moved_with_a_one_line_pointer():
    text = page()
    assert 'Days from drilling to abandonment</h2>' not in text
    assert 'id="fig-days"' not in text and 'Table B1' not in text
    assert ('<p>The days at each stage of a well\'s life, from drilling to abandonment, move to the plugging-and-abandonment '
            'article of this series.</p>') in text
    parked = ROOT.parent / 'plug_abandonment_article'
    for name in ['README.md', 'section3-days.md', 'days_charts.py', 'days_charts.js', 'data/days-summary.csv']:
        assert (parked / name).stat().st_size > 0, name


def appendix(name, end):
    return re.search(r'<h2 id="' + name + r'">(.*?)' + end, page(), re.S).group(1)


def test_appendices_are_purpose_bullets_and_a_link():
    a = appendix('reusable-prompts', '<h2 id="counting-rules">')
    b = appendix('counting-rules', '<div class="foot">')
    for part, link in [(a, '/tree/' + '[0-9a-f]{40}' + '/examples/bsee/issue2_public_data_r12/prompts"'),
                       (b, '/blob/' + '[0-9a-f]{40}' + '/examples/bsee/issue2_public_data_r12/counting-rules.md"')]:
        assert len(re.findall('<li>', part)) == 2
        assert re.search(link, part)
        assert len(re.sub(r'<[^>]+>', '', part)) < 500


def test_full_appendix_text_is_in_the_repository():
    rules = (ROOT / 'counting-rules.md').read_text(encoding='utf-8')
    prompts = (ROOT / 'prompts' / 'README.md').read_text(encoding='utf-8')
    for text in (rules, prompts):
        assert not re.search(r'@@[^@\s]+@@', text)
        assert not re.search(r'\b[A-Za-z]:[\\/]|/mnt/|/home/|Users[\\/]', text)
    old = (R10 / 'issue2-public-data-r10.html').read_text(encoding='utf-8')
    b2 = re.search(r'<h3>B.2 Detailed counting rules and exclusions</h3>\n<ul>(.*?)</ul>', old, re.S).group(1)
    for item in re.findall(r'<li>(.*?)</li>', b2):
        words = re.sub(r'<[^>]+>', '', item).split()[:6]
        plain = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', rules.replace('`', ''))
        assert ' '.join(words).replace('`', '') in re.sub(r'\s+', ' ', plain), words
    assert rules.count('| Drilling (recorded spud to total depth) |') == 5   # Table B1: four bands and missing depth
    assert 'Reproduce the published result' in prompts and 'Check values:' in prompts


# ---- notes before titles, on every figure and table ---------------------------------------------------------------

def test_notes_come_before_every_figure_and_table_title():
    text = page()
    titles = re.findall(r'<p class="ft">((?:Figure|Table) [0-9A-Z]+) - ', text)
    assert titles == ['Figure 1', 'Figure 2', 'Figure 3', 'Figure 4', 'Figure 5', 'Table 1']
    for title in titles:
        assert re.search(r'</ol>\n<p class="ft">' + title + ' - ', text), title
    assert not re.search(r'<p class="ft">[^<]*</p>\s*<ol class="fn">', text)


# ---- the page as a whole ------------------------------------------------------------------------------------------

def test_infographic_carries_the_band_counts_and_opens_the_article():
    text = page()
    order = [text.index(x) for x in ['<h1>', 'class="ig"', '<section class="intro"', '<nav class="toc"', '<h2 id="s1">']]
    assert order == sorted(order)
    for label in ['Objective', 'Starting point', 'What we did', 'What we found', 'What you can do']:
        assert f'<p class="ig-k">{label}</p>' in text
    scene = re.search(r'<div class="ig-scene">(.*?)</div>', text, re.S).group(1)
    for a, b in [('1,089', '33'), ('126', '10'), ('209', '95'), ('160', '108')]:
        assert f'>{a} &#8594; {b}<' in scene


def test_page_is_complete_and_under_the_commit_limit():
    raw = PAGE_FILE.read_bytes()
    assert len(raw) < build.SIZE_LIMIT
    assert not re.search(r'@@[^@\s]+@@', raw.decode('utf-8'))


def test_no_local_paths_in_the_page():
    text = re.sub(r'data:image/png;base64,[A-Za-z0-9+/=]+', '', page())
    assert not re.search(r'\b[A-Za-z]:[\\/]|/mnt/|/home/|Users[\\/]', text)


HARNESS = r"""
const s=require('fs').readFileSync(0,'utf8');const plots=[],els={},timers=[],made=[];
const node=tag=>{const n={tag,style:{},attrs:{},children:[],handlers:{},setAttribute(k,v){this.attrs[k]=v;},append(...c){this.children.push(...c);},
addEventListener(t,f){this.handlers[t]=f;},insertBefore(c){made.push(c);}};return n;};
const el=id=>els[id]||(els[id]=Object.assign(node('div'),{id,clientWidth:900,parentNode:node('div'),on(n,f){this.handlers['plotly:'+n]=f;}}));
global.window={IntersectionObserver:undefined};global.getComputedStyle=()=>({getPropertyValue:()=>' #123456 '});
global.setInterval=(f,ms)=>{timers.push({f,ms});return timers.length;};global.clearInterval=()=>{};
global.document={documentElement:{},createElement:node,querySelectorAll:()=>[],getElementById:id=>el(id),querySelector:()=>({hidden:false})};
const calls=[];
global.Plotly={Plots:{resize(){}},newPlot(e,t,l){plots.push({id:e.id,n:t.length,bg:l.paper_bgcolor,layout:l,names:t.map(x=>x.name)});return Promise.resolve();},
restyle(e,u){calls.push(['restyle',e.id,u.x?u.x.map(a=>a.length):null]);return Promise.resolve();},relayout(e,u){calls.push(['relayout',e.id]);return Promise.resolve();}};
new Function(s)();
setTimeout(()=>{const box=made[0];const out=box&&box.children[2];
const before=out&&out.textContent;if(timers[0])timers[0].f();const after=out&&out.textContent;
els['fig-map'].handlers.mousedown&&els['fig-map'].handlers.mousedown();
els['fig-map-trend'].handlers['plotly:plotly_click']({points:[{x:2015}]});const clicked=out&&out.textContent;
process.stdout.write(JSON.stringify({plots,timers:timers.length,before,after,clicked,calls}));},0);
"""


def run_script():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js is needed for the chart script test')
    script = re.findall(r'<script>([\s\S]*?)</script>', page())[-1]
    done = subprocess.run([node, '-e', HARNESS], input=script, capture_output=True, text=True, encoding='utf-8', timeout=120, check=True)
    return json.loads(done.stdout)


def test_chart_script_draws_every_chart():
    result = run_script()
    assert [p['id'] for p in result['plots']] == [c['id'] for c in chart_data()]
    assert len(result['plots']) == 6 and all(p['bg'] == '#ffffff' for p in result['plots'])


def test_map_plays_windows_until_a_click_then_follows_panel_b():
    result = run_script()
    assert result['timers'] == 1                          # playing starts without a click
    assert result['before'] == '2005 to 2009: 1,584 new wells'
    assert result['after'].startswith('2006 to 2010: ')     # one tick moves one year
    assert result['clicked'].startswith('2011 to 2015: 626 new wells')
    shown = [c[2] for c in result['calls'] if c[0] == 'restyle']
    assert sum(shown[0]) == 1584


def test_figures_have_png_and_svg_exports():
    for name in build.IMAGES:
        assert (ROOT / 'figures' / (name + '.png')).stat().st_size > 0
        assert (ROOT / 'figures' / (name + '.svg')).stat().st_size > 0


def test_manifest_lists_hashes_that_match():
    for item in build.manifest():
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256']


def test_sign_off_awaits_review_of_revision_12():
    text = page()
    sign_off = re.findall(r'<p class="dc">(.*?)</p>', text)
    assert sign_off == ["Prepared: Analyst Deckhand &middot; Checked: Editor Deckhand &middot; "
                        "Approved: awaiting the maintainer's review of revision 12"]
    assert '3 November 2026' not in sign_off[0] and 'Approved: Vamsee' not in text
    # "3 November 2026" stays only as the retrieval date of the permit file
    assert len(re.findall(r'\b3 November 2026', text)) == text.count('retrieved 3 November 2026')


def test_one_or_two_hypotheses_and_the_data_set_named():
    text = page()
    assert 1 <= text.count('<p>Our hypothesis:') <= 2
    assert ('The public data set is two BSEE raw data files (permits to drill, boreholes) and the EIA WTI spot '
            'price.') in text
    assert '<p class="ft">Sources: BSEE raw data files; EIA WTI spot price (section 1, Figure 1).' in text
    assert '<p>To try it out or adapt the analysis, see <a href="#reusable-prompts">reusable prompt</a>.</p>' in text


def test_what_we_found_reads_as_reviewed():
    text = ('New wells moved to deep water: 68.8 % were in less than 100 m in 2005 to 2009, 13.4 % in 2021 to 2025. '
            'After the oil price fell in 2015, shallow-water wells fell the most.')
    assert '<p class="ig-k">What we found</p><p>' + text + '</p>' in page()


# ---- revision 12: cues that send the reader to the right place --------------------------------------------------

def test_right_axis_of_panel_b_takes_the_oil_colour_and_both_axes_name_their_line_style():
    trend = {p['id']: p for p in run_script()['plots']}['fig-map-trend']['layout']
    right, left = trend['yaxis2'], trend['yaxis']
    assert right['title']['font']['color'] == right['tickfont']['color'] == right['linecolor'] == build.OIL
    assert 'WTI oil price (USD/bbl)' in right['title']['text'] and build.RIGHT_NOTE in right['title']['text']
    assert 'New wells started (-)' in left['title']['text'] and build.LEFT_NOTE in left['title']['text']
    assert build.RIGHT_NOTE == 'right axis: dashed line' and build.LEFT_NOTE == 'left axis: solid lines and dots'
    assert 'Dashed line: oil price (right axis)' in trend['legend']['title']['text']


def test_panel_b_key_points_are_the_section_1_readings():
    marks = charts()['fig-map-trend']['marks']
    assert [(m['x'], m['y'], m['axis']) for m in marks] == [(2015, 48.69, 'y2'), (2017, 12.33, 'y')]
    assert marks[0]['text'] == 'Oil price fell: USD 93 to 49\n(2014 to 2015)' and marks[0]['colour'] == build.OIL
    assert marks[1]['text'] == 'Under 100 m, 3-year mean: about 62 a year\n(2012 to 2014) to about 12 (2015 to 2017)'


def test_bar_key_points_hold_in_the_data():
    found = charts()
    for chart, what in [('fig-rig', 'drillships'), ('fig-depth', '500 m or more')]:
        marks = found[chart]['marks']
        assert marks[0]['x'] == 2015 and marks[0]['text'] == f'From 2015, {what}:\nover half of the permits each year'
        assert marks[1]['x'] == 2026 and 'part year' in marks[1]['text'] and '2 November 2026' in marks[1]['text']
    rig = pd.read_csv(ROOT / 'data' / 'fig-p1-new-well-permits-by-rig-type.csv')
    full = rig[rig.year.between(2015, 2025)]
    assert (full.Drillship / full.total > .5).all() and rig.loc[rig.year.eq(2014), 'Drillship'].item() / rig.loc[rig.year.eq(2014), 'total'].item() <= .5
    depth = pd.read_csv(ROOT / 'data' / 'new-well-permits-by-water-depth.csv')
    share = (depth['500_to_1500_m'] + depth['1500_m_and_deeper']) / depth.permits
    assert (share[depth.year.between(2015, 2025)] > .5).all() and share[depth.year.eq(2014)].item() <= .5
    assert build.majority_from([.6, .4, .6, .7], [2005, 2006, 2007, 2008]) == 2007
    with pytest.raises(ValueError):   # a reading that no longer holds stops the build
        build.bar_marks(rig.assign(Drillship=0), build.RIGS, 'rig')


def test_legend_titles_say_how_to_read_the_colours():
    found = charts()
    assert found['fig-map']['key'] == found['pies-depth']['key'] == build.DEPTH_KEY == 'Water depth (light = shallow, dark = deep)'
    assert found['fig-depth']['key'].startswith(build.DEPTH_KEY) and 'stacked from the bottom' in found['fig-rig']['key']
    plots = {p['id']: p for p in run_script()['plots']}
    assert plots['fig-map']['names'][1:] == ['Under 100 m (1,089)', '100 to 500 m (126)', '500 to 1,500 m (209)', '1,500 m and deeper (160)']
