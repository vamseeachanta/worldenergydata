"""Offline checks of the revision 10 page: counts and day statistics unchanged from revision 9, one validated
water-depth palette, median and N on every stage chart, notes before every title, and a working chart script."""
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
PAGE_FILE = ROOT / 'issue2-public-data-r10.html'
spec = importlib.util.spec_from_file_location('build_r10', ROOT / 'build_r10.py')
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


def page():
    return PAGE_FILE.read_text(encoding='utf-8')


def chart_data():
    return json.loads(re.search(r'const charts=(\[.*?\]);\n', page(), re.S).group(1))


# ---- counts and day statistics stay those of revision 9 ----------------------------------------------------------

def test_every_input_matches_its_pin():
    build.validate_inputs()


def test_reused_data_files_are_byte_identical_to_revision_9():
    for name in build.REUSED:
        assert (ROOT / 'data' / (name + '.csv')).read_bytes() == (R9 / 'data' / (name + '.csv')).read_bytes(), name


@pytest.mark.parametrize('name', ['pies-rig', 'pies-depth'])
def test_regenerated_pie_shares_equal_revision_9(name):
    assert (ROOT / 'data' / (name + '.csv')).read_bytes() == (R9 / 'data' / (name + '.csv')).read_bytes()


def test_check_values_in_appendix_a_are_unchanged():
    text = page()
    old = (R9 / 'issue2-public-data-r9.html').read_text(encoding='utf-8')
    for pattern in [r'Check values: .*?Completion estimate medians by band: [^<]*d\.', r'From 2005 to 2026, [\d,]+ wells are counted this way']:
        assert re.search(pattern, text).group(0) == re.search(pattern, old).group(0)


def test_overview_medians_equal_the_day_summary():
    stats = pd.read_csv(ROOT / 'data' / 'days-summary.csv')
    overview = pd.read_csv(ROOT / 'data' / 'days-overview.csv')
    assert len(overview) == 20
    for activity in build.ACTIVITIES:
        rows = build.stage_rows(stats, activity)
        part = overview[overview.stage.eq(build.STAGES[activity][1])].set_index('band').loc[build.BANDS]
        assert part.median_days.tolist() == rows.median_days.tolist()
        assert part.n.tolist() == rows.n.astype(int).tolist()
    # hand check: drilling under 100 m, median of the recorded spud-to-total-depth days, 21 d over 1,507 boreholes
    first = overview.iloc[0]
    assert (first.stage, first.band, int(first.n), first.median_days) == ('Drilling', 'Under 100 m', 1507, 21.0)
    # hand check: completion at 1,500 m and deeper, 40 d over 1,566 permits
    row = overview[(overview.stage == 'Completion') & (overview.band == '1,500 m and deeper')].iloc[0]
    assert (int(row.n), row.median_days) == (1566, 40.0)


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
    for chart in chart_data():
        if chart['kind'] in ('interval', 'grouped', 'byband'):
            assert chart['colours'] == build.WC
        if chart['id'] == 'fig-depth':
            assert chart['colours'] == build.WC
        if chart['id'] == 'pies-depth':
            assert all(set(p['colours']) <= set(build.WC) for p in chart['pies'])
        if chart['id'] == 'fig-map':
            assert [t['colour'] for t in chart['traces'][:4]] == build.WC


def test_slice_labels_use_dark_ink_on_light_fills():
    assert build.ink_on('#F0E442') == build.INK
    assert build.ink_on('#0b3d5c') == '#ffffff'


# ---- Figure 6 and the stage charts (Figure 7) ---------------------------------------------------------------------

def test_every_stage_chart_shows_the_median_beside_n():
    stats = pd.read_csv(ROOT / 'data' / 'days-summary.csv')
    charts = {c['id']: c for c in chart_data()}
    for activity in build.ACTIVITIES:
        chart = charts['days-' + build.STAGES[activity][0]]
        rows = build.stage_rows(stats, activity)
        for label, r in zip(chart['label'], rows.itertuples()):
            assert label.startswith('Median ' + build.significant(r.median_days) + ' d · N ')
            assert label.endswith(build.count_display(r.n).lstrip('≈'))
    assert build.count_label(1507) == 'N = 1,507'
    assert build.count_label(23216) == 'N ≈ 23,220'


def test_figure_6_has_both_views_with_twenty_medians():
    charts = {c['id']: c for c in chart_data()}
    for name in ['days-overview-stage', 'days-overview-depth']:
        assert len(charts[name]['rows']) == 20
        assert charts[name]['stages'] == [build.STAGES[a][1] for a in build.ACTIVITIES]


def figure_notes(number):
    block = re.search(r'<figcaption>\n<ol class="fn">(.*?)</ol>\n<p class="ft">Figure ' + str(number) + ' - ', page(), re.S)
    assert block, number
    return block.group(1)


@pytest.mark.parametrize('number', [6, 7])
def test_n_and_median_are_defined_in_the_notes(number):
    notes = figure_notes(number)
    assert '<li>Median: the middle value.' in notes
    assert '<li>N: the number of records behind' in notes


# ---- notes before titles, on every figure and table ---------------------------------------------------------------

def test_notes_come_before_every_figure_and_table_title():
    text = page()
    titles = re.findall(r'<p class="ft">((?:Figure|Table) [0-9A-Z]+) - ', text)
    assert titles == ['Figure 1', 'Figure 2', 'Figure 3', 'Figure 4', 'Figure 5', 'Table 1', 'Figure 6', 'Figure 7', 'Table B1']
    for title in titles:
        assert re.search(r'</ol>\n<p class="ft">' + title + ' - ', text), title
    assert not re.search(r'<p class="ft">[^<]*</p>\s*<ol class="fn">', text)


# ---- the page as a whole ------------------------------------------------------------------------------------------

def test_infographic_and_introduction_open_the_article():
    text = page()
    order = [text.index(x) for x in ['<h1>', 'class="ig"', '<section class="intro"', '<nav class="toc"', '<h2 id="s1">']]
    assert order == sorted(order)
    for label in ['Objective', 'Starting point', 'What we did', 'What we found', 'What you can do']:
        assert f'<p class="ig-k">{label}</p>' in text
    assert 'blockquote class="takeaway"' not in text


def test_page_is_complete_and_under_the_commit_limit():
    raw = PAGE_FILE.read_bytes()
    assert len(raw) < build.SIZE_LIMIT
    assert not re.search(r'@@[^@\s]+@@', raw.decode('utf-8'))


def test_no_local_paths_in_the_page():
    text = re.sub(r'data:image/png;base64,[A-Za-z0-9+/=]+', '', page())
    assert not re.search(r'\b[A-Za-z]:[\\/]|/mnt/|/home/|Users[\\/]', text)


def test_chart_script_draws_every_chart():
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node.js is needed for the chart script test')
    script = re.findall(r'<script>([\s\S]*?)</script>', page())[-1]
    harness = r"""
const s=require('fs').readFileSync(0,'utf8');const plots=[],els={};
const el=id=>els[id]||(els[id]={id,style:{},clientWidth:900,handlers:{},on(n,f){this.handlers[n]=f;}});
global.window={};global.getComputedStyle=()=>({getPropertyValue:()=>' #123456 '});
global.document={documentElement:{},querySelectorAll:()=>[],getElementById:id=>el(id),querySelector:()=>({hidden:false})};
global.Plotly={Plots:{resize(){}},newPlot(e,t,l){plots.push({id:e.id,n:t.length,bg:l.paper_bgcolor});return Promise.resolve();},restyle(){return Promise.resolve();}};
new Function(s)();setTimeout(()=>process.stdout.write(JSON.stringify(plots)),0);
"""
    done = subprocess.run([node, '-e', harness], input=script, capture_output=True, text=True, encoding='utf-8', timeout=120, check=True)
    plots = json.loads(done.stdout)
    assert [p['id'] for p in plots] == [c['id'] for c in chart_data()]
    assert len(plots) == 12 and all(p['bg'] == '#ffffff' for p in plots)


def test_figures_have_png_and_svg_exports():
    for name in build.IMAGES:
        assert (ROOT / 'figures' / (name + '.png')).stat().st_size > 0
        assert (ROOT / 'figures' / (name + '.svg')).stat().st_size > 0


def test_manifest_lists_hashes_that_match():
    for item in build.manifest():
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256']
