"""Rebuild the revision 11 public-data page.

Revision 11 changes, after the maintainer's review of revision 10 (18 November 2026):
- the infographic puts the new-well counts of each water-depth band in the scene;
- Figure 1 plays through every five-year window from 2005 to 2009 to 2021 to 2025 until the reader clicks, and
  panel b gives the new wells started each year by water depth, with three-year rolling averages beside the
  annual WTI oil price;
- section 3 (days from drilling to abandonment) moves to the series' plugging-and-abandonment article; its text and
  code are kept in ../plug_abandonment_article/;
- Appendix A and Appendix B keep short purpose bullets and a link; their full text is written to prompts/README.md
  and counting-rules.md next to this script.

Permit counts (Figures 2 to 5, Table 1) are the revision 9 data files, pinned by SHA-256 and copied unchanged. The
yearly wells of Figure 1 come from derive_r11.py (same borehole file and rule as revision 9); the WTI series is the
repository snapshot data/wti-monthly.csv (US EIA). inputs/manifest.json pins every one of them.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import re
import shutil
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
TAG = 'r11'
PAGE = 'issue2-public-data-r11.html'
FOLDER = 'examples/bsee/issue2_public_data_r11'
REPO = 'https://github.com/vamseeachanta/worldenergydata'
R9 = '../issue2_public_data_r9/data/'
WTI_COMMIT = '37e36be7c19d7e121d2d1208aff61ca9e6b1bb59'   # commit that added data/wti-monthly.csv (pull request 1185)
BANDS = ['Under 100 m', '100 to 500 m', '500 to 1,500 m', '1,500 m and deeper']
# Life of a well: drilling, completion, intervention, temporary then permanent abandonment.
ACTIVITIES = ['Spud to total depth', 'Completion', 'Intervention',
              'Temporary abandonment', 'Permanent abandonment']
RECORDED = 'Spud to total depth'
STAGES = {'Spud to total depth': ('drilling', 'Drilling', 'recorded spud to total depth'),
          'Completion': ('completion', 'Completion', 'operator estimate'),
          'Intervention': ('intervention', 'Intervention', 'operator estimate'),
          'Temporary abandonment': ('temporary-abandonment', 'Temporary abandonment', 'operator estimate'),
          'Permanent abandonment': ('permanent-abandonment', 'Permanent abandonment', 'operator estimate')}
RIGS = ['Jack-up', 'Drillship', 'Semisubmersible', 'DP semisubmersible',
        'Platform rig', 'Submersible', 'Other']
# Rig types (Figures 2 and 3), unchanged from revision 9: the two brand colours, then the Okabe-Ito set.
RC = ['#0b3d5c', '#2BB2A6', '#E69F00', '#56B4E9', '#CC79A7', '#D55E00', '#8a8985']
# Water depth (Figures 1, 4 and 5): the revision 10 palette, ordered light to dark so a deeper band reads darker.
# Okabe-Ito yellow, brand teal, Okabe-Ito blue, brand navy; validated in tests/test_build_r11.py.
WC = ['#F0E442', '#2BB2A6', '#0072B2', '#0b3d5c']
OIL = '#D55E00'     # Okabe-Ito vermilion: the oil price, apart from every depth colour
EDGE = '#5a6b76'
INK = '#26323a'
WK = ['under_100_m', '100_to_500_m', '500_to_1500_m', '1500_m_and_deeper']
PIE_YEARS = [2005, 2015, 2025]
YEARS = list(range(2005, 2026))
WINDOW = 5          # map frames: five-year windows, 2005 to 2009 up to 2021 to 2025, one year apart
ROLL = 3            # panel b: trailing three-year rolling average, full windows only
SUMMARY_PERIODS = [(2005, 2009), (2021, 2025)]
STATIC_WINDOWS = [(2005, 2009), (2013, 2017), (2021, 2025)]
PRICE_STEP = (2014, 2015)   # the year-on-year fall the observation reads, checked against the data
MAP_BOX = (-98.0, -80.0, 18.0, 31.0)       # lon min, lon max, lat min, lat max shown
CLAMP_BOX = (-101.0, -77.0, 15.0, 34.0)    # land rings are clamped to this larger box
LAND = 'ne_50m_land.geojson'
NE_COMMIT = 'f1890d9f152c896d250a77557a5751a93d494776'  # natural-earth-vector tag v5.1.2
PLOTLY = 'plotly-2.35.2.min.js'
FILES = {PLOTLY: 'https://cdn.plot.ly/plotly-2.35.2.min.js',
         LAND: f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{NE_COMMIT}/geojson/{LAND}'}
SIZE_LIMIT = 1_024_000   # check-added-large-files --maxkb=1000 in .pre-commit-config.yaml
# Revision 9 data files reused unchanged and copied into data/ (the page or counting-rules.md links each one).
REUSED = ['days-summary', 'map-wells', 'map-summary', 'map-selection', 'sources', 'exclusions',
          'repeat-key-sensitivity', 'code_mapping', 'subtype-activity', 'source-members', 'source_columns',
          'fig-p1-new-well-permits-by-rig-type', 'new-well-permits-by-water-depth', 'table1']
DERIVED = ['map-wells-by-year', 'new-wells-by-year', 'wti-annual']   # written by derive_r11.py, pinned


def significant(value, digits=4):
    return format(float(value), f'.{digits}g') if value is not None and math.isfinite(float(value)) else 'Not available'


def count_display(value):
    rounded = float(significant(value))
    return ('≈' if rounded != value else '') + format(rounded, ',.0f')


def pie_years(years):
    if not set(PIE_YEARS).issubset(set(years)):
        raise ValueError('Missing fixed representative full year')
    return list(PIE_YEARS)


def ink_on(colour):
    """Dark text on light fills (yellow, teal, orange, sky blue), white text on dark fills."""
    r, g, b = (int(colour.lstrip('#')[i:i + 2], 16) / 255 for i in (0, 2, 4))
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (r, g, b)]
    luminance = 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]
    return INK if luminance > 0.18 else '#ffffff'


def period_name(a, b):
    return f'{a} to {b}'


def map_observation(summary):
    first, last = [summary.loc[period_name(a, b)] for a, b in SUMMARY_PERIODS]
    share = lambda row: row['Under 100 m'] / row.total * 100
    deep = lambda row: (row['500 to 1,500 m'] + row['1,500 m and deeper']) / row.total * 100
    if not share(last) < share(first):
        raise ValueError('Review the map observation: shallow share did not fall')
    if not deep(last) > deep(first):
        raise ValueError('Review the map observation: deep share did not rise')
    return (f'Of the {first.total:,} new wells started from 2005 to 2009, {share(first):.1f} % were in less than 100 m of water '
            f'and {deep(first):.1f} % in 500 m or more; of the {last.total:,} started from 2021 to 2025, '
            f'{share(last):.1f} % and {deep(last):.1f} %')


def clamp_ring(ring, box=CLAMP_BOX):
    lo0, lo1, la0, la1 = box
    out = []
    for lon, lat in ring:
        point = (round(min(max(lon, lo0), lo1), 3), round(min(max(lat, la0), la1), 3))
        if not out or out[-1] != point:
            out.append(point)
    return out


def land_rings(path, box=CLAMP_BOX):
    """Natural Earth land rings touching the clamp box, clamped to it (outer and inner rings)."""
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    rings = []
    for feature in data['features']:
        geometry = feature['geometry']
        polygons = geometry['coordinates'] if geometry['type'] == 'MultiPolygon' else [geometry['coordinates']]
        for polygon in polygons:
            for ring in polygon:
                if any(box[0] <= x <= box[1] and box[2] <= y <= box[3] for x, y in ring):
                    clamped = clamp_ring(ring, box)
                    if len(clamped) >= 4 and len(set(clamped)) >= 3:
                        rings.append(clamped)
    if not rings:
        raise ValueError('No land in the map box')
    return rings


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_source(cache, name, url, offline, expected_sha=None):
    path = cache / name
    receipt = path.with_suffix('.receipt.json')
    if not path.exists():
        if offline:
            raise FileNotFoundError(f'Offline cache missing: {name}')
        content = fetch(url)
        if expected_sha and hashlib.sha256(content).hexdigest() != expected_sha:
            raise ValueError(f'Download differs from issued source pin: {name}')
        path.write_bytes(content)
        record = dict(file=name, url=url, retrieved_utc=datetime.now(timezone.utc).isoformat(), sha256=sha(path))
        receipt.write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    record = json.loads(receipt.read_text(encoding='utf-8'))
    if record['url'] != url or record['sha256'] != sha(path):
        raise ValueError(f'Cache receipt mismatch: {name}')
    if expected_sha and record['sha256'] != expected_sha:
        raise ValueError(f'Cache differs from issued source pin: {name}')
    return record


def write_csv(frame, out, name):
    frame.to_csv(out / 'data' / (name + '.csv'), index=False, lineterminator='\n', float_format='%.12g')


def save_figure(fig, out, name):
    fig.savefig(out / 'figures' / (name + '.png'), dpi=150, metadata={'Software': TAG})
    fig.savefig(out / 'figures' / (name + '.svg'), metadata={'Date': None, 'Creator': TAG})
    svg = out / 'figures' / (name + '.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8', newline='\n')
    plt.close(fig)


MAP_LABELS = [(-90.0, 24.6, 'Gulf of America\n(Gulf of Mexico)')]


def windows():
    """Every five-year window of 2005 to 2025, one year apart: 2005 to 2009, 2006 to 2010, ... 2021 to 2025."""
    return [(end - WINDOW + 1, end) for end in range(YEARS[0] + WINDOW - 1, YEARS[-1] + 1)]


def window_counts(counts):
    """New wells in each window by band, from the yearly counts (the map shows exactly these wells)."""
    rows = []
    for a, b in windows():
        part = counts[counts.year.between(a, b)]
        rows.append(dict(start=a, end=b, **{band: int(part[band].sum()) for band in BANDS}, total=int(part.total.sum())))
    return pd.DataFrame(rows)


def map_figure(wells, rings, counts, summary, out):
    """Figure 1a: wells by water-depth band in every five-year window (played in the page); three windows on paper."""
    per = window_counts(counts)
    for a, b in SUMMARY_PERIODS:   # the windows of the revision 9 periods equal the revision 9 map summary
        row = per[(per.start == a) & (per.end == b)].iloc[0]
        if [int(row[x]) for x in BANDS + ['total']] != [int(summary.loc[period_name(a, b)][x]) for x in BANDS + ['total']]:
            raise ValueError(f'Window {a} to {b} differs from the revision 9 map summary')
    aspect = 1 / math.cos(math.radians(sum(MAP_BOX[2:]) / 2))
    fig, axes = plt.subplots(1, len(STATIC_WINDOWS), figsize=(14, 4.6), layout='constrained')
    for ax, (a, b) in zip(axes, STATIC_WINDOWS):
        for ring in rings:
            xs, ys = zip(*ring)
            ax.fill(xs, ys, color='#e4e2dc', edgecolor='#a9a69e', linewidth=.4, zorder=1)
        part = wells[wells.spud_year.between(a, b)]
        for band, colour in zip(BANDS, WC):
            p = part[part.band.eq(band)]
            ax.scatter(p.longitude, p.latitude, s=7, color=colour, label=band, edgecolors=EDGE, linewidths=.25, zorder=2)
        ax.text(*MAP_LABELS[0][:2], MAP_LABELS[0][2], ha='center', va='center', fontsize=8, color='#4f6d7a', style='italic')
        ax.set(xlim=MAP_BOX[:2], ylim=MAP_BOX[2:], xlabel='Longitude (°)', ylabel='Latitude (°)')
        ax.set_aspect(aspect)
        ax.set_facecolor('#f4f8fb')
        ax.set_title(f'{period_name(a, b)}: {len(part):,} wells', fontsize=11)
    handles = [plt.Line2D([], [], marker='o', linestyle='', color=c, markeredgecolor=EDGE, label=b) for b, c in zip(BANDS, WC)]
    fig.legend(handles=handles, loc='outside upper center', ncol=4, fontsize=9, title='Water depth')
    save_figure(fig, out, 'fig-map')
    write_csv(per, out, 'map-windows')
    traces = []
    for band, colour in zip(BANDS, WC):
        p = wells[wells.band.eq(band)]
        traces.append(dict(band=band, colour=colour, lon=[round(v, 3) for v in p.longitude], lat=[round(v, 3) for v in p.latitude],
                           depth=[round(v) for v in p.water_depth_m], year=[int(v) for v in p.spud_year]))
    frames = [dict(start=int(r['start']), end=int(r['end']), label=f"{period_name(r['start'], r['end'])}: {int(r['total']):,} new wells",
                   counts=[int(r[b]) for b in BANDS]) for _, r in per.iterrows()]
    return dict(id='fig-map', kind='map', box=MAP_BOX, aspect=aspect, bands=BANDS, edge=EDGE, frames=frames,
                land=[[list(pt) for pt in ring] for ring in rings], traces=traces, labels=MAP_LABELS, step_ms=1300)


def rolling(counts):
    """Trailing three-year mean of the yearly counts, for full windows only (first value at 2007)."""
    frame = counts.set_index('year')[BANDS + ['total']]
    return frame.rolling(ROLL, min_periods=ROLL).mean()


def trend_table(counts, wti):
    roll = rolling(counts)
    table = counts.set_index('year')[BANDS + ['total']].copy()
    for column in BANDS + ['total']:
        table[column + ' (3-year mean)'] = roll[column].round(2)
    table['WTI (USD/bbl)'] = wti.set_index('year').wti_usd_per_bbl
    if table['WTI (USD/bbl)'].isna().any():
        raise ValueError('WTI annual mean missing for a year of Figure 1b')
    return table.reset_index()


def trend_figure(table, out):
    """Figure 1b: new wells started each year by water depth (dots), three-year rolling means (lines), WTI (right)."""
    fig, ax = plt.subplots(figsize=(11, 4.8), layout='constrained')
    for band, colour in zip(BANDS, WC):
        ax.plot(table.year, table[band], 'o', color=colour, markeredgecolor=EDGE, markersize=4, alpha=.8)
        ax.plot(table.year, table[band + ' (3-year mean)'], '-', color=EDGE, linewidth=3.6)
        ax.plot(table.year, table[band + ' (3-year mean)'], '-', color=colour, linewidth=2.4, label=band)
    ax.set(xlabel='Spud year', ylabel='New wells started (-)', xlim=(YEARS[0] - .5, YEARS[-1] + .5), ylim=(0, None))
    ax.grid(axis='y', alpha=.2)
    right = ax.twinx()
    right.plot(table.year, table['WTI (USD/bbl)'], '--', color=OIL, linewidth=1.6, label='WTI oil price (annual mean)')
    right.set(ylabel='WTI oil price (USD/bbl)', ylim=(0, None))
    right.spines['right'].set_visible(True)
    lines = ax.get_legend_handles_labels()[0][::1] + right.get_legend_handles_labels()[0]
    labels = [l + ' (3-year mean)' for l in BANDS] + ['WTI oil price (annual mean)']
    ax.legend(lines, labels, ncol=3, fontsize=8, loc='upper right')
    save_figure(fig, out, 'fig-map-trend')
    write_csv(table, out, 'new-wells-trend')
    return dict(id='fig-map-trend', kind='trend', years=[int(y) for y in table.year], bands=BANDS, colours=WC, edge=EDGE, oil=OIL,
                counts=[[int(v) for v in table[b]] for b in BANDS],
                means=[[None if pd.isna(v) else float(v) for v in table[b + ' (3-year mean)']] for b in BANDS],
                wti=[float(v) for v in table['WTI (USD/bbl)']], roll=ROLL, window=WINDOW)


def trend_values(table):
    """The rolling-average reading: WTI annual means either side of the fall and the three-year averages before and
    after it, under 100 m and in 500 m or more; it fails closed if the reading no longer holds."""
    t = table.set_index('year')
    a, b = PRICE_STEP
    before, after = (a - ROLL + 1, a), (b, b + ROLL - 1)
    shallow = [t.loc[w[1], 'Under 100 m (3-year mean)'] for w in (before, after)]
    deep_cols = ['500 to 1,500 m', '1,500 m and deeper']
    deep = [sum(t.loc[w[1], c + ' (3-year mean)'] for c in deep_cols) for w in (before, after)]
    price = [t.loc[a, 'WTI (USD/bbl)'], t.loc[b, 'WTI (USD/bbl)']]
    if not (price[1] < price[0] * .6 and shallow[1] < shallow[0] * .5 and deep[0] * .6 < deep[1] < deep[0]):
        raise ValueError('Review the rolling-average observation')
    return dict(price=price, shallow=shallow, deep=deep, before=before, after=after)


def trend_observation(table):
    """The rolling-average bullet in section 1, with the averages rounded to whole wells; the exact values are in the
    Figure 1 notes (trend_note)."""
    v = trend_values(table)
    a, b = PRICE_STEP
    return (f'When the WTI oil price fell from USD {v["price"][0]:.2f} a barrel in {a} to USD {v["price"][1]:.2f} in {b} '
            f'(annual means), the three-year average of new wells in less than 100 m of water fell from about '
            f'{v["shallow"][0]:.0f} a year ({period_name(*v["before"])}) to about {v["shallow"][1]:.0f} '
            f'({period_name(*v["after"])}); in 500 m or more it fell from about {v["deep"][0]:.0f} to about {v["deep"][1]:.0f}')


def trend_note(table):
    """The Figure 1 note with the exact three-year averages behind the section 1 observation."""
    v = trend_values(table)
    return (f'Section 1 reads these three-year averages, new wells a year: under 100 m, {v["shallow"][0]:.1f} '
            f'({period_name(*v["before"])}) and {v["shallow"][1]:.1f} ({period_name(*v["after"])}); 500 m or more, '
            f'{v["deep"][0]:.1f} and {v["deep"][1]:.1f}.')


def count_figures(rig, depth, out):
    payload = []
    for frame, keys, labels, colours, kind in [(rig, RIGS, RIGS, RC, 'rig'), (depth, WK, BANDS, WC, 'depth')]:
        fig, ax = plt.subplots(figsize=(11, 4.8), layout='constrained')
        bottom = pd.Series(0, index=frame.index)
        for key, label, colour in zip(keys, labels, colours):
            edge = dict(edgecolor=EDGE, linewidth=.5) if kind == 'depth' else {}
            ax.bar(frame.year, frame[key], bottom=bottom, label=label, color=colour, **edge)
            bottom += frame[key]
        ax.set(xlabel='Year of requested spud date', ylabel='New-well permits (-)')
        ax.legend(ncol=3, fontsize=8, loc='upper right')
        save_figure(fig, out, 'fig-' + kind)
        payload.append(dict(id='fig-' + kind, kind='bar', rows=frame.to_dict('records'), keys=keys, labels=labels, colours=colours,
                            edge=EDGE if kind == 'depth' else None))
        payload.append(pie_set(frame, keys, labels, colours, kind, out))
    return payload


def pie_set(frame, keys, labels, colours, kind, out):
    """One figure per set: a pie per year, the year alone above each pie, one shared legend."""
    pie_rows, pies = [], []
    fig, axes = plt.subplots(1, len(PIE_YEARS), figsize=(12, 5.4), layout='constrained')
    for ax, year in zip(axes, pie_years(frame.year)):
        row = frame[frame.year.eq(year)].iloc[0]
        values = [int(row[k]) for k in keys]
        total = sum(values)
        pie_rows.extend(dict(year=year, category=l, permits=v, total=total, share_percent=v / total * 100) for l, v in zip(labels, values))
        shown = [(v, l, c) for v, l, c in zip(values, labels, colours) if v > 0]
        values, pie_labels, pie_colours = map(list, zip(*shown))
        shares = [f'{v / total * 100:.1f}%' for v in values]
        wedges, _ = ax.pie(values, colors=pie_colours, startangle=90, counterclock=False, wedgeprops={'edgecolor': 'white'})
        label_shares(ax, wedges, pie_labels, values, shares, total, pie_colours)
        ax.set_title(str(year), fontsize=12)
        pies.append(dict(year=year, total=total, values=values, labels=pie_labels, colours=pie_colours, shares=shares,
                         inks=[ink_on(c) for c in pie_colours], small=small_share_lines(pie_labels, values, shares, total)))
    used = [(l, c) for l, c in zip(labels, colours) if any(l in p['labels'] for p in pies)]
    handles = [plt.Rectangle((0, 0), 1, 1, facecolor=c, edgecolor=EDGE if kind == 'depth' else c, linewidth=.5) for _, c in used]
    fig.legend(handles, [l for l, _ in used], loc='outside lower center', ncol=len(used), fontsize=9)
    name = 'pies-' + kind
    save_figure(fig, out, name)
    write_csv(pd.DataFrame(pie_rows), out, name)
    return dict(id=name, kind='pieset', pies=pies)


def small_share_lines(labels, values, shares, total, per_line=2):
    """Shares under 5 % as short lines printed under the pie, so no label is lost or overlaps."""
    small = [f'{l} {s}' for l, v, s in zip(labels, values, shares) if v / total * 100 < 5]
    return ['Under 5%:'] + ['; '.join(small[i:i + per_line]) for i in range(0, len(small), per_line)] if small else []


def label_shares(ax, wedges, labels, values, shares, total, colours):
    """Every share is printed: inside the slice for 5 % or more, in a list under the pie below 5 %."""
    for wedge, value, share, colour in zip(wedges, values, shares, colours):
        if value / total * 100 >= 5:
            angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
            ax.text(.68 * math.cos(angle), .68 * math.sin(angle), share, ha='center', va='center', fontsize=9, color=ink_on(colour))
    lines = small_share_lines(labels, values, shares, total)
    if lines:
        ax.text(0, -1.12, '\n'.join(lines), ha='center', va='top', fontsize=8.5, color='#333333')


def pie_totals(pieset):
    return ', '.join(f"{p['total']:,} in {p['year']}" for p in pieset['pies'])


def stage_rows(stats, activity):
    return stats[(stats.activity == activity) & stats.band.isin(BANDS)].set_index('band').loc[BANDS]


def stage_name(activity):
    _, name, basis = STAGES[activity]
    return f'{name} ({basis})'


def page_date(value):
    date = datetime.fromisoformat(value[:10])
    return f'{date.day} {date.strftime("%B %Y")}'


def scene_svg(summary):
    """Infographic scene: the four water-depth bands as water over a stepped seabed in the depth colours. Each band
    carries its new-well count and share, 2005 to 2009 then 2021 to 2025 (map summary), in the space the band leaves
    free: on the seabed under shallow water, in the water itself where the water is deep. Below, the stages of a
    well's life, with drilling marked as this article."""
    first, last = [summary.loc[period_name(a, b)] for a, b in SUMMARY_PERIODS]
    w, x0, sea, bed = 1040, 20, 58, 150
    col = (w - 2 * x0) / 4
    depths = [22, 50, 104, 146]   # drawn water depth of each band, shallow to deep (not to scale)
    parts = [f'<svg class="ig-svg" viewBox="0 0 {w} 350" role="img" aria-labelledby="ig-scene-t">'
             '<title id="ig-scene-t">The four water-depth bands of this article as water over a stepped seabed, light to dark from shallow '
             'to deep, each with its new wells started in 2005 to 2009 and in 2021 to 2025 and their share of all new wells; below, '
             'the five stages of a well\'s life in order, with drilling marked as the stage this article covers</title>',
             f'<rect x="{x0}" y="{sea}" width="{w - 2 * x0}" height="{bed}" fill="#e4e2dc"/>',
             f'<line x1="{x0}" x2="{w - x0}" y1="{sea}" y2="{sea}" stroke="#0b3d5c" stroke-width="1.5"/>',
             f'<text x="{x0}" y="{sea - 34}" class="ig-t">Shelf: jack-ups</text>',
             f'<text x="{w - x0}" y="{sea - 34}" class="ig-t" text-anchor="end">Deep water: drillships</text>',
             f'<text x="{w / 2}" y="{sea - 30}" class="ig-n" text-anchor="middle">New wells started, 2005 to 2009 &#8594; 2021 to 2025</text>',
             f'<text x="{w / 2}" y="{sea - 12}" class="ig-n" text-anchor="middle">(share of all new wells in the period)</text>']
    for i, (band, colour, d) in enumerate(zip(BANDS, WC, depths)):
        x = x0 + i * col
        cx = x + col / 2
        parts.append(f'<rect x="{x:.1f}" y="{sea}" width="{col:.1f}" height="{d}" fill="{colour}" stroke="{EDGE}" stroke-width=".8"/>')
        in_water = d >= 100
        ink = ink_on(colour) if in_water else INK
        top = sea + 30 if in_water else sea + d + 34
        a, b = int(first[band]), int(last[band])
        sa, sb = a / first.total * 100, b / last.total * 100
        parts.append(f'<text x="{cx:.1f}" y="{top}" class="ig-big" text-anchor="middle" fill="{ink}">{a:,} &#8594; {b:,}</text>')
        parts.append(f'<text x="{cx:.1f}" y="{top + 24}" class="ig-s" text-anchor="middle" fill="{ink}">{sa:.1f} % &#8594; {sb:.1f} %</text>')
        parts.append(f'<text x="{cx:.1f}" y="{sea + bed + 22}" class="ig-t" text-anchor="middle">{html.escape(band)}</text>')
    y, n = 282, len(ACTIVITIES)
    step = (w - 2 * x0) / n
    for i, activity in enumerate(ACTIVITIES):
        x = x0 + i * step
        name = STAGES[activity][1]
        here = activity == RECORDED
        fill, stroke = ('#2BB2A6', '#0b3d5c') if here else ('#ffffff', '#8a98a3')
        parts.append(f'<rect x="{x + 4:.1f}" y="{y}" width="{step - 26:.1f}" height="44" fill="{fill}" stroke="{stroke}" stroke-width="1.2"'
                     + ('' if here else ' stroke-dasharray="4 3"') + '/>')
        words = name.split(' ')
        lines = [name] if len(words) == 1 else [words[0], ' '.join(words[1:])]
        for k, line in enumerate(lines):
            parts.append(f'<text x="{x + 4 + (step - 26) / 2:.1f}" y="{y + (27 if len(lines) == 1 else 19 + 16 * k)}" class="ig-t" text-anchor="middle">{line}</text>')
        if i < n - 1:
            ax = x + step - 20
            parts.append(f'<path d="M{ax:.1f} {y + 22} h14 m-5 -5 l5 5 l-5 5" fill="none" stroke="#0e7e88" stroke-width="2"/>')
    parts.append(f'<text x="{x0}" y="{y - 10}" class="ig-n">The life of a well: this article covers new wells (solid); the later stages follow in this series (dashed)</text>')
    parts.append('</svg>')
    return ''.join(parts)


def infographic_found(summary, table):
    """The "What we found" panel, generated from the map summary and the yearly trend."""
    first, last = [summary.loc[period_name(a, b)] for a, b in SUMMARY_PERIODS]
    shallow = [row['Under 100 m'] / row.total * 100 for row in (first, last)]
    deep = [(row['500 to 1,500 m'] + row['1,500 m and deeper']) / row.total * 100 for row in (first, last)]
    trend_observation(table)   # fails closed if the rolling-average reading no longer holds
    if not (shallow[1] < shallow[0] and deep[1] > deep[0]):
        raise ValueError('Review the infographic statement')
    return (f'New wells moved to deep water: {shallow[0]:.1f} % were in less than 100 m in 2005 to 2009, '
            f'{shallow[1]:.1f} % in 2021 to 2025. After the oil price fell in {PRICE_STEP[1]}, shallow-water wells fell the most.')


BUILD_COMMIT = None  # set from the required --build-commit: full SHA of the commit that holds this script


def require_https(url):
    """Reject every scheme except https (no file:, ftp:, http: or data: reads)."""
    if urllib.parse.urlsplit(url).scheme != 'https':
        raise ValueError('Only https downloads are allowed: ' + url)
    return url


class HttpsOnlyRedirect(urllib.request.HTTPRedirectHandler):
    """Follow a redirect only when its target is also https."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return super().redirect_request(req, fp, code, msg, headers, require_https(newurl))


def https_opener():
    """Opener with an https handler only; no file, ftp, data or plain-http handler is installed."""
    opener = urllib.request.OpenerDirector()
    for handler in (urllib.request.HTTPSHandler(), HttpsOnlyRedirect(),
                    urllib.request.HTTPDefaultErrorHandler(), urllib.request.HTTPErrorProcessor()):
        opener.add_handler(handler)
    return opener


def fetch(url, timeout=600):
    url = require_https(url)   # checked before any opener exists
    with https_opener().open(url, timeout=timeout) as response:
        return response.read()


def check_build_commit(value):
    """Issued rebuilds cite an immutable revision: a full 40-character commit SHA, never a branch."""
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('--build-commit needs the full 40-character SHA of the commit that holds this script')
    return value


def plotly_script(cache, bundle=False):
    """Tracked page: pinned release URL with a sub-resource integrity hash of the pinned bytes.
    Bundle: the same pinned bytes inlined, for an offline interactive copy kept outside the repository."""
    library = (cache / PLOTLY).read_bytes()
    if bundle:
        text = library.decode('utf-8')
        if '</script' in text.lower():
            raise ValueError('Unexpected script closing tag in library')
        return '<script>' + text + '</script>'
    integrity = 'sha384-' + base64.b64encode(hashlib.sha384(library).digest()).decode()
    return f'<script src="{FILES[PLOTLY]}" integrity="{integrity}" crossorigin="anonymous"></script>'


def write_pages(out, cache, page, bundle=None):
    if re.search(r'@@[^@\s]+@@', page.replace('@@PLOTLY_SCRIPT@@', '')):
        raise ValueError('Unresolved page token')
    tracked = page.replace('@@PLOTLY_SCRIPT@@', plotly_script(cache)).encode('utf-8')
    if len(tracked) >= SIZE_LIMIT:
        raise ValueError(f'Page is {len(tracked):,} bytes; the commit limit is {SIZE_LIMIT:,}')
    (out / PAGE).write_bytes(tracked)
    if bundle is not None:
        bundle = bundle.resolve()
        if bundle == ROOT or ROOT in bundle.parents:
            raise ValueError('Write the bundled page outside the tracked example folder')
        bundle.parent.mkdir(parents=True, exist_ok=True)
        bundle.write_bytes(page.replace('@@PLOTLY_SCRIPT@@', plotly_script(cache, bundle=True)).encode('utf-8'))


def versions():
    import sys
    return f'Python {sys.version.split()[0]}, pandas {pd.__version__} and matplotlib {matplotlib.__version__}'


def map_footnote(summary, audit):
    parts = []
    for period, row in summary.iterrows():
        bands = '; '.join(f'{b[0].lower() + b[1:]}: {row[b]:,}' for b in BANDS)
        parts.append(f'{period}: {row.total:,} wells ({bands})')
    dropped = int(audit.missing_or_outside_coordinates.sum())
    return '; '.join(parts) + f'. Wells without coordinates in the map area: {dropped:,}.'


IMAGES = ['fig-map', 'fig-map-trend', 'fig-rig', 'pies-rig', 'fig-depth', 'pies-depth']


def page_png(path, colours=256):
    """The static fallback embedded in the page: the exported PNG reduced to a 256-colour palette, which keeps the
    flat chart colours and the tracked page under the commit limit. The full PNG and SVG stay in figures/."""
    from io import BytesIO
    from PIL import Image
    with Image.open(path) as image:
        reduced = image.convert('RGB').quantize(colors=colours, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    buffer = BytesIO()
    reduced.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()


# ---- the two repository files that hold Appendix A and Appendix B in full ----------------------------------------

def md_days_table(stats):
    columns = ['Stage and basis', 'Water depth', 'Records (-)', 'Used (-)', 'Missing/invalid (-)', 'Nonpositive (-)', 'Q1 (d)', 'Median (d)', 'Q3 (d)']
    lines = ['| ' + ' | '.join(columns) + ' |', '| --- | --- | ' + ' | '.join(['---:'] * 7) + ' |']
    for row in stats.itertuples():
        counts = [row.records, row.n, row.missing_invalid_days, row.nonpositive_days]
        values = [stage_name(row.activity), row.band] + [count_display(v) for v in counts] + [significant(v) for v in [row.q1_days, row.median_days, row.q3_days]]
        lines.append('| ' + ' | '.join(values) + ' |')
    return '\n'.join(lines)


def fill_markdown(template, values):
    text = (ROOT / 'inputs' / template).read_text(encoding='utf-8')
    for key, value in values.items():
        text = text.replace('@@' + key + '@@', value)
    if re.search(r'@@[^@\s]+@@', text):
        raise ValueError('Unresolved token in ' + template)
    return text


def write_markdown(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def source_lines(sources):
    holds = {'APDRawData.zip (file of 2 November 2026)': ('Application for Permit to Drill', 'file of 2 November 2026', 'permit type, requested spud date, water depth, rig name and rig type'),
             'BoreholeRawData.zip': ('Boreholes', '@@FILEDATE@@', 'region, well-name suffix, spud date, status, water depth and surface location')}
    lines = []
    for r in sources.itertuples():
        if r.file in holds:
            name, date, what = holds[r.file]
            lines.append(f'- {name} ([{r.file.split(" ")[0]}]({r.url})), {date.replace("@@FILEDATE@@", "file of " + page_date(r.file_date))}, '
                         f'downloaded {page_date(r.retrieved_utc)}, SHA-256 `{r.sha256}`: {what}.')
    land = sources[sources.file.eq(LAND)].iloc[0]
    lines.append(f'- Map land outline: Natural Earth 1:50m land ([{LAND}]({land.url}), version 5.1.2, public domain), downloaded '
                 f'{page_date(land.retrieved_utc)}, SHA-256 `{land.sha256}`.')
    lines.append(f'- Oil price: US Energy Information Administration, Cushing WTI spot price, monthly, as the repository snapshot '
                 f'[data/wti-monthly.csv]({REPO}/blob/{WTI_COMMIT}/data/wti-monthly.csv) (retrieved 12 October 2026; provenance in '
                 f'[wti-monthly.PROVENANCE.md]({REPO}/blob/{WTI_COMMIT}/data/wti-monthly.PROVENANCE.md)); annual means in data/wti-annual.csv.')
    return '\n'.join(lines)


def appendix_files(out, stats, sources, audit, summary, counts):
    check = pd.read_csv(out / 'data' / 'repeat-key-sensitivity.csv')
    delta = (check.latest_key_median_days - check.median_days).abs().dropna()
    sensitivity = f'{len(delta[delta.gt(0)])} of {len(delta)} comparable cell medians change. The largest absolute change is {significant(delta.max())} d.'
    dates = {}
    for token, source in [('APM', 'eWellAPMRawData.zip'), ('BORE', 'BoreholeRawData.zip'), ('SCHEMA', 'APDRawData.zip')]:
        row = sources[sources.file.eq(source)].iloc[0]
        dates[token + '_DATE'] = page_date(row.retrieved_utc)
        dates[token + '_FILE'] = page_date(row.file_date)
    audit_md = '\n'.join(f'- {r.source}: {r.rule.replace("_", " ")}: {count_display(r.records)} records.' for r in audit.itertuples())
    rules = fill_markdown('counting-rules-template.md', dict(dates, SENSITIVITY_RESULT=sensitivity, AUDIT=audit_md,
                                                             DAYS_DETAIL_TABLE=md_days_table(stats)))
    write_markdown(out / 'counting-rules.md', rules)
    check_map = ' and '.join(f'{row.total:,} ({period})' for period, row in summary.iterrows())
    prompts = fill_markdown('prompts-template.md', dict(dates, VERSIONS=versions(), SOURCES=source_lines(sources), CHECK_MAP=check_map,
                                                        CHECK_YEARS=', '.join(f'{int(r.total)} ({int(r.year)})' for r in counts.itertuples() if r.year in (2005, 2015, 2025))))
    write_markdown(out / 'prompts' / 'README.md', prompts)


def build_html(out, cache, payload, sources, map_info, table):
    page = (ROOT / 'inputs' / 'page-template.html').read_text(encoding='utf-8')
    land = sources[sources.file.eq(LAND)].iloc[0]
    page = page.replace('@@BUILD_COMMIT@@', BUILD_COMMIT).replace('@@BUILD_SHORT@@', BUILD_COMMIT[:8])
    page = page.replace('@@MAP_OBSERVATION@@', html.escape(map_observation(map_info['summary'])))
    page = page.replace('@@TREND_OBSERVATION@@', html.escape(trend_observation(table)))
    page = page.replace('@@TREND_NOTE@@', html.escape(trend_note(table)))
    page = page.replace('@@MAP_COUNTS@@', html.escape(map_footnote(map_info['summary'], map_info['audit'])))
    page = page.replace('@@IG_FOUND@@', html.escape(infographic_found(map_info['summary'], table)))
    page = page.replace('@@IG_SCENE@@', scene_svg(map_info['summary']))
    page = page.replace('@@WTI_URL@@', f'{REPO}/blob/{WTI_COMMIT}/data/wti-monthly.csv')
    page = page.replace('@@WTI_PROV_URL@@', f'{REPO}/blob/{WTI_COMMIT}/data/wti-monthly.PROVENANCE.md')
    for chart in payload:
        if chart['kind'] == 'pieset':
            page = page.replace('@@PIE_TOTALS_' + chart['id'].split('-')[1].upper() + '@@', pie_totals(chart))
    page = page.replace('@@LAND_DATE@@', page_date(land.retrieved_utc)).replace('@@LAND_URL@@', land.url)
    row = sources[sources.file.eq('BoreholeRawData.zip')].iloc[0]
    page = page.replace('@@BORE_DATE@@', page_date(row.retrieved_utc)).replace('@@BORE_FILE@@', page_date(row.file_date))
    page = page.replace('@@CHART_DATA@@', json.dumps(payload, separators=(',', ':'), ensure_ascii=False).replace('<', '\\u003c'))
    for name in IMAGES:
        page = page.replace('@@IMAGE:' + name + '@@', 'data:image/png;base64,' + base64.b64encode(page_png(out / 'figures' / (name + '.png'))).decode())
    return page


def manifest():
    return json.loads((ROOT / 'inputs' / 'manifest.json').read_text(encoding='utf-8'))


def validate_inputs():
    """Every input, the revision 9 data files and the derived Figure 1 files included, must match its pinned SHA-256."""
    for item in manifest():
        if sha(ROOT / item['path']) != item['sha256']:
            raise ValueError('Retained input hash mismatch: ' + item['path'])


def copy_reused(out):
    """Copy reused and derived pinned data files, byte for byte, to data/."""
    pinned = {Path(i['path']).name for i in manifest()}
    for name in REUSED + DERIVED:
        if name + '.csv' not in pinned:
            raise ValueError('Data file is not pinned: ' + name)
    for name in REUSED + DERIVED:
        source = ROOT / (R9 if name in REUSED else Path('data')) / (name + '.csv')
        target = out / 'data' / (name + '.csv')
        if source.resolve() != target.resolve():
            shutil.copyfile(source, target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'cache')
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--build-commit', required=True,
                        help='full 40-character SHA of the commit that holds this script, linked from the appendices')
    parser.add_argument('--bundle', type=Path, default=None,
                        help='also write an offline interactive copy with the pinned chart library inlined; '
                             'the path must lie outside this example folder')
    args = parser.parse_args(argv)
    global BUILD_COMMIT
    try:
        BUILD_COMMIT = check_build_commit(args.build_commit)
    except ValueError as error:
        parser.error(str(error))
    out, cache = args.output_dir.resolve(), args.data_dir.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    for folder in ['data', 'figures']:
        (out / folder).mkdir(parents=True, exist_ok=True)
    validate_inputs()
    pins = json.loads((ROOT / 'inputs' / 'source-pins.json').read_text(encoding='utf-8'))
    if set(pins) != set(FILES):
        raise ValueError('Every source needs an issued pin')
    for name, url in FILES.items():
        cache_source(cache, name, url, args.offline, pins[name])
    copy_reused(out)
    read = lambda name: pd.read_csv(out / 'data' / (name + '.csv'))
    stats, sources, audit = read('days-summary'), read('sources'), read('exclusions')
    sources = sources.fillna('')
    map_audit = read('map-selection')
    summary = read('map-summary').set_index('period')
    wells = pd.read_csv(out / 'data' / 'map-wells-by-year.csv', dtype={'api_well_number': str})
    counts = pd.read_csv(out / 'data' / 'new-wells-by-year.csv')
    wti = pd.read_csv(out / 'data' / 'wti-annual.csv')
    rig, depth = read('fig-p1-new-well-permits-by-rig-type'), read('new-well-permits-by-water-depth')
    if not rig.total.equals(depth.permits) or not rig.year.equals(depth.year):
        raise ValueError('Annual totals differ between the rig-type and water-depth files')
    if len(wells) != int(counts.total.sum()):
        raise ValueError('Yearly counts differ from the mapped wells')
    matplotlib.rcParams.update({'svg.hashsalt': 'issue2-public-data-' + TAG, 'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    table = trend_table(counts, wti)
    payload = ([map_figure(wells, land_rings(cache / LAND), counts, summary, out), trend_figure(table, out)]
               + count_figures(rig, depth, out))
    appendix_files(out, stats, sources, audit, summary, counts)
    page = build_html(out, cache, payload, sources, dict(summary=summary, audit=map_audit), table)
    write_pages(out, cache, page, args.bundle)
    print(table.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
