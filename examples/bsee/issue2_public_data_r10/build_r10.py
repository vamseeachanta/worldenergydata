"""Rebuild the revision 10 public-data page from the pinned revision 9 data files.

Revision 10 changes the presentation only: one water-depth palette for every figure, a combined
median-days chart, median and count labels on every stage chart, notes above each figure title and
the objective infographic. Counts and day statistics are read, byte for byte, from the revision 9
data files, which build_r9.py derived from the BSEE raw data; inputs/manifest.json pins each one.
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
TAG = 'r10'
PAGE = 'issue2-public-data-r10.html'
R9 = '../issue2_public_data_r9/data/'
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
# Water depth (Figures 1, 4, 5, 6 and 7): the same family as the rig types, ordered light to dark, so a
# deeper band always reads darker. Okabe-Ito yellow, brand teal, Okabe-Ito blue, brand navy. Checked by
# tests/test_build_r10.py: CIE L* falls band by band for normal vision and for simulated protan, deutan and
# tritan vision (Machado, Oliveira and Fernandes 2009, severity 1.0), and every pair is at least 15 CIEDE2000
# apart in all four. Yellow is below 3:1 on white, so yellow marks carry a dark edge and every bar its value.
WC = ['#F0E442', '#2BB2A6', '#0072B2', '#0b3d5c']
EDGE = '#5a6b76'
INK = '#26323a'
WK = ['under_100_m', '100_to_500_m', '500_to_1500_m', '1500_m_and_deeper']
PIE_YEARS = [2005, 2015, 2025]
MAP_PERIODS = [(2005, 2009), (2021, 2025)]
MAP_BOX = (-98.0, -80.0, 18.0, 31.0)       # lon min, lon max, lat min, lat max shown
CLAMP_BOX = (-101.0, -77.0, 15.0, 34.0)    # land rings are clamped to this larger box
LAND = 'ne_50m_land.geojson'
NE_COMMIT = 'f1890d9f152c896d250a77557a5751a93d494776'  # natural-earth-vector tag v5.1.2
PLOTLY = 'plotly-2.35.2.min.js'
FILES = {PLOTLY: 'https://cdn.plot.ly/plotly-2.35.2.min.js',
         LAND: f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{NE_COMMIT}/geojson/{LAND}'}
SIZE_LIMIT = 1_024_000   # check-added-large-files --maxkb=1000 in .pre-commit-config.yaml
# Revision 9 data files reused unchanged and copied into data/ (the page links each one).
REUSED = ['days-summary', 'map-wells', 'map-summary', 'map-selection', 'sources', 'exclusions',
          'repeat-key-sensitivity', 'code_mapping', 'subtype-activity', 'source-members', 'source_columns',
          'fig-p1-new-well-permits-by-rig-type', 'new-well-permits-by-water-depth', 'table1']


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


def map_observation(summary):
    first, last = [summary.loc[f'{a} to {b}'] for a, b in MAP_PERIODS]
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


def map_figure(wells, rings, out):
    """Two map panels, one per period, wells coloured by water-depth band."""
    aspect = 1 / math.cos(math.radians(sum(MAP_BOX[2:]) / 2))
    fig, axes = plt.subplots(1, 2, figsize=(12, 5.4), layout='constrained')
    periods = [f'{a} to {b}' for a, b in MAP_PERIODS]
    for ax, period in zip(axes, periods):
        for ring in rings:
            xs, ys = zip(*ring)
            ax.fill(xs, ys, color='#e4e2dc', edgecolor='#a9a69e', linewidth=.4, zorder=1)
        part = wells[wells.period.eq(period)]
        for band, colour in zip(BANDS, WC):
            p = part[part.band.eq(band)]
            ax.scatter(p.longitude, p.latitude, s=9, color=colour, label=band, edgecolors=EDGE, linewidths=.25, zorder=2)
        ax.text(*MAP_LABELS[0][:2], MAP_LABELS[0][2], ha='center', va='center', fontsize=9, color='#4f6d7a', style='italic')
        ax.set(xlim=MAP_BOX[:2], ylim=MAP_BOX[2:], xlabel='Longitude (°)', ylabel='Latitude (°)')
        ax.set_aspect(aspect)
        ax.set_facecolor('#f4f8fb')
        ax.set_title(period, fontsize=11)
    handles = [plt.Line2D([], [], marker='o', linestyle='', color=c, markeredgecolor=EDGE, label=b) for b, c in zip(BANDS, WC)]
    fig.legend(handles=handles, loc='outside upper center', ncol=4, fontsize=9, title='Water depth')
    save_figure(fig, out, 'fig-map')
    traces = []
    for i, period in enumerate(periods):
        part = wells[wells.period.eq(period)]
        for band, colour in zip(BANDS, WC):
            p = part[part.band.eq(band)]
            traces.append(dict(axis=i, band=band, colour=colour, lon=[round(v, 4) for v in p.longitude],
                lat=[round(v, 4) for v in p.latitude], depth=[round(v) for v in p.water_depth_m], year=[int(v) for v in p.spud_year]))
    return dict(id='fig-map', kind='map', periods=periods, box=MAP_BOX, aspect=aspect, bands=BANDS, edge=EDGE,
                land=[[list(pt) for pt in ring] for ring in rings], traces=traces, labels=MAP_LABELS)


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


def none_if_nan(value):
    return None if value is None or not math.isfinite(float(value)) else float(value)


def count_label(n):
    """N = 1,507; a count rounded to four significant figures reads N ≈ 23,220."""
    shown = count_display(n)
    return 'N ≈ ' + shown[1:] if shown.startswith('≈') else 'N = ' + shown


def stage_label(median, n):
    """The label beside each depth band on a stage chart: the median, then the count behind it."""
    return f'Median {significant(median)} d · {count_label(n)}'


def days_figures(stats, out):
    """One small interval chart per stage of well life, in life order, each band labelled with median and N."""
    payload = []
    for activity in ACTIVITIES:
        slug, _, _ = STAGES[activity]
        rows = stage_rows(stats, activity)
        fig, ax = plt.subplots(figsize=(8, 2.7), layout='constrained')
        for i, (_, row) in enumerate(rows.iterrows()):
            if row.n:
                ax.plot([row.q1_days, row.q3_days], [i, i], color=EDGE, linewidth=4.6, solid_capstyle='butt')
                ax.plot([row.q1_days, row.q3_days], [i, i], color=WC[i], linewidth=3, solid_capstyle='butt')
                ax.plot(row.median_days, i, 'o', color=WC[i], markeredgecolor='#0b3d5c')
                ax.annotate(stage_label(row.median_days, row.n), (row.q3_days, i), xytext=(6, -3), textcoords='offset points', fontsize=8)
        ax.set(xlabel='Days (d)', yticks=range(4), yticklabels=BANDS, xlim=(0, max(1, rows.q3_days.max()) * 1.8))
        ax.grid(axis='x', alpha=.2)
        ax.invert_yaxis()
        save_figure(fig, out, 'days-' + slug)
        payload.append(dict(id='days-' + slug, kind='interval', bands=BANDS, colours=WC, edge=EDGE,
            q1=[none_if_nan(v) for v in rows.q1_days], median=[none_if_nan(v) for v in rows.median_days],
            q3=[none_if_nan(v) for v in rows.q3_days], n=[int(v) for v in rows.n],
            nlabel=[count_label(v) for v in rows.n], label=[stage_label(r.median_days, r.n) for r in rows.itertuples()],
            shown=[[significant(v) for v in (r.q1_days, r.median_days, r.q3_days)] for r in rows.itertuples()]))
    return payload


STAGE_TICKS = {'Spud to total depth': 'Drilling', 'Completion': 'Completion', 'Intervention': 'Intervention',
               'Temporary abandonment': 'Temporary\nabandonment', 'Permanent abandonment': 'Permanent\nabandonment'}


def overview_table(stats):
    """Median days and N for every stage and water-depth band, in the order of a well's life."""
    rows = []
    for activity in ACTIVITIES:
        for band, r in stage_rows(stats, activity).iterrows():
            rows.append(dict(stage=STAGES[activity][1], basis=STAGES[activity][2], band=band, n=int(r.n), median_days=r.median_days))
    return pd.DataFrame(rows)


def overview_figures(stats, out):
    """Figure 6: the median days of every stage in the four bands, (a) by stage in life order, (b) by water depth."""
    table = overview_table(stats)
    write_csv(table, out, 'days-overview')
    stages = [STAGES[a][1] for a in ACTIVITIES]
    ticks = [STAGE_TICKS[a] for a in ACTIVITIES]
    top = table.median_days.max() * 1.18
    # (a) by stage: five groups in life order, four bars each, one per water-depth band
    fig, ax = plt.subplots(figsize=(11, 4.6), layout='constrained')
    width = .2
    for j, (band, colour) in enumerate(zip(BANDS, WC)):
        part = table[table.band.eq(band)].set_index('stage').loc[stages]
        xs = [i + (j - 1.5) * width for i in range(len(stages))]
        ax.bar(xs, part.median_days, width=width, color=colour, edgecolor=EDGE, linewidth=.5, label=band)
        for x, m in zip(xs, part.median_days):
            ax.text(x, m + top * .012, significant(m), ha='center', va='bottom', fontsize=7.5, color=INK)
    ax.set(xticks=range(len(stages)), xticklabels=ticks, ylabel='Median days (d)', ylim=(0, top))
    ax.legend(ncol=4, fontsize=8.5, loc='upper right', title='Water depth', title_fontsize=8.5)
    ax.grid(axis='y', alpha=.2)
    save_figure(fig, out, 'days-overview-stage')
    # (b) by water depth: four blocks, five stage bars each in life order, in the band's colour
    fig, ax = plt.subplots(figsize=(11, 7), layout='constrained')
    ys, labels, k = [], [], 1
    for band, colour in zip(BANDS, WC):
        part = table[table.band.eq(band)].set_index('stage').loc[stages]
        pos = [k + i for i in range(len(stages))]
        ax.barh(pos, part.median_days, color=colour, edgecolor=EDGE, linewidth=.5, height=.75)
        for y, m in zip(pos, part.median_days):
            ax.text(m + top * .008, y, significant(m), va='center', fontsize=8, color=INK)
        ax.text(0, k - .75, band, ha='left', va='bottom', fontsize=9.5, fontweight='bold', color=INK)
        ys += pos
        labels += stages
        k += len(stages) + 1.4
    ax.set(yticks=ys, yticklabels=labels, xlabel='Median days (d)', xlim=(0, top))
    ax.invert_yaxis()
    ax.grid(axis='x', alpha=.2)
    save_figure(fig, out, 'days-overview-depth')
    records = [dict(stage=r.stage, band=r.band, median=float(r.median_days), shown=significant(r.median_days),
                    nlabel=count_label(r.n)) for r in table.itertuples()]
    return [dict(id='days-overview-stage', kind='grouped', bands=BANDS, colours=WC, edge=EDGE, stages=stages,
                 ticks=[t.replace('\n', '<br>') for t in ticks], rows=records, top=top),
            dict(id='days-overview-depth', kind='byband', bands=BANDS, colours=WC, edge=EDGE, stages=stages,
                 rows=records, top=top)]


def day_observations(csv_path):
    """Section 3.1 bullets, in the order of a well's life, read from the summary CSV."""
    stats = pd.read_csv(csv_path).set_index(['activity', 'band'])
    medians = {a: stats.loc[a].loc[BANDS, 'median_days'] for a in ACTIVITIES}
    if not all(medians[a].map(math.isfinite).all() for a in ACTIVITIES):
        raise ValueError('Observations require medians for all four depth bands')
    bullets = []
    for activity, label in [(RECORDED, 'Drilling: recorded spud-to-total-depth'), ('Completion', 'Completion: estimate')]:
        values = medians[activity]
        if not values.is_monotonic_increasing or values.iloc[0] >= values.iloc[-1]:
            raise ValueError('Review rising-median observation: ' + activity)
        bullets.append(f'{label} medians rise with water depth, from {significant(values.iloc[0])} d under 100 m to {significant(values.iloc[-1])} d at 1,500 m and deeper.')
    for activity, label in [('Intervention', 'Intervention'), ('Temporary abandonment', 'Temporary abandonment'),
                            ('Permanent abandonment', 'Permanent abandonment')]:
        values = medians[activity]
        bullets.append(f'{label}: estimate medians range from {significant(values.min())} to {significant(values.max())} d across the four depth bands.')
    return bullets


def page_date(value):
    date = datetime.fromisoformat(value[:10])
    return f'{date.day} {date.strftime("%B %Y")}'


def stage_name(activity):
    _, name, basis = STAGES[activity]
    return f'{name} ({basis})'


def days_table(stats, detailed=False):
    columns = ['Stage and basis', 'Water depth', 'Used (-)', 'Q1 (d)', 'Median (d)', 'Q3 (d)']
    if detailed:
        columns[2:3] = ['Records (-)', 'Used (-)', 'Missing/invalid (-)', 'Nonpositive (-)']
    else:
        if stats.loc[~stats.band.isin(BANDS), 'records'].sum():
            raise ValueError('Selected records have missing depth; review the page statement')
        stats = stats[stats.band.isin(BANDS)]
    rows = []
    for row in stats.itertuples():
        counts = [row.records, row.n, row.missing_invalid_days, row.nonpositive_days] if detailed else [row.n]
        values = [stage_name(row.activity), row.band] + [count_display(v) for v in counts] + [significant(v) for v in [row.q1_days, row.median_days, row.q3_days]]
        rows.append('<tr>' + ''.join('<td>' + html.escape(v) + '</td>' for v in values) + '</tr>')
    return '<div class="nl-tablewrap days-table"><table><thead><tr>' + ''.join('<th scope="col">' + c + '</th>' for c in columns) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def days_panels():
    """The five stage charts of Figure 7, each labelled by its stage only."""
    parts = []
    for letter, activity in zip('abcde', ACTIVITIES):
        slug, name, basis = STAGES[activity]
        alt = f'{name}: median and quartile days by water-depth band, with the median and N beside each band'
        parts.append(f'<div class="stage"><p class="stage-label">{letter}. {name} <span class="basis">({basis})</span></p>'
                     f'<div id="days-{slug}" class="viz" style="height:230px" role="img" aria-label="{alt}"></div>'
                     f'<img class="chart-fallback" data-for="days-{slug}" src="@@IMAGE:days-{slug}@@" alt="{alt}"></div>')
    return ''.join(parts)


def scene_svg():
    """Infographic scene: the four water-depth bands as a stepped seabed in the depth colours, and the
    stages of a well's life in order. Drawn from BANDS, WC and STAGES; no number of ours is on it."""
    w, x0, sea = 1040, 20, 46
    col = (w - 2 * x0) / 4
    depths = [34, 62, 96, 132]
    parts = [f'<svg class="ig-svg" viewBox="0 0 {w} 300" role="img" aria-labelledby="ig-scene-t">'
             '<title id="ig-scene-t">The four water-depth bands of this article as a stepped seabed, light to dark from shallow to deep, '
             'with jack-ups on the shelf and drillships in deep water; below, the five stages of a well\'s life in order: '
             'drilling, completion, intervention, temporary abandonment and permanent abandonment</title>',
             f'<rect x="{x0}" y="{sea}" width="{w - 2 * x0}" height="{max(depths) + 4}" fill="#eef4f8"/>',
             f'<line x1="{x0}" x2="{w - x0}" y1="{sea}" y2="{sea}" stroke="#0b3d5c" stroke-width="1.5"/>',
             f'<text x="{x0}" y="{sea - 30}" class="ig-t">Shelf: jack-ups</text>',
             f'<text x="{w - x0}" y="{sea - 30}" class="ig-t" text-anchor="end">Deep water: drillships</text>',
             f'<text x="{w / 2}" y="{sea - 10}" class="ig-n" text-anchor="middle">Water depth, shallow to deep</text>']
    for i, (band, colour, d) in enumerate(zip(BANDS, WC, depths)):
        x = x0 + i * col
        parts.append(f'<rect x="{x:.1f}" y="{sea + d}" width="{col:.1f}" height="{max(depths) + 4 - d}" fill="{colour}" stroke="{EDGE}" stroke-width=".8"/>')
        parts.append(f'<text x="{x + col / 2:.1f}" y="{sea + max(depths) + 24}" class="ig-t" text-anchor="middle">{html.escape(band)}</text>')
    y, n = 230, len(ACTIVITIES)
    step = (w - 2 * x0) / n
    for i, activity in enumerate(ACTIVITIES):
        x = x0 + i * step
        name = STAGES[activity][1]
        parts.append(f'<rect x="{x + 4:.1f}" y="{y}" width="{step - 26:.1f}" height="44" fill="#ffffff" stroke="#0b3d5c" stroke-width="1.2"/>')
        words = name.split(' ')
        lines = [name] if len(words) == 1 else [words[0], ' '.join(words[1:])]
        for k, line in enumerate(lines):
            parts.append(f'<text x="{x + 4 + (step - 26) / 2:.1f}" y="{y + (27 if len(lines) == 1 else 19 + 16 * k)}" class="ig-t" text-anchor="middle">{line}</text>')
        if i < n - 1:
            ax = x + step - 20
            parts.append(f'<path d="M{ax:.1f} {y + 22} h14 m-5 -5 l5 5 l-5 5" fill="none" stroke="#0e7e88" stroke-width="2"/>')
    parts.append(f'<text x="{x0}" y="{y - 10}" class="ig-n">The life of a well, in order</text>')
    parts.append('</svg>')
    return ''.join(parts)


def infographic_found(summary, stats):
    """The "What we found" panel, generated from the map summary and the day statistics."""
    first, last = [summary.loc[f'{a} to {b}'] for a, b in MAP_PERIODS]
    shallow = [row['Under 100 m'] / row.total * 100 for row in (first, last)]
    deep = [(row['500 to 1,500 m'] + row['1,500 m and deeper']) / row.total * 100 for row in (first, last)]
    drill = stage_rows(stats, RECORDED).median_days
    if not (shallow[1] < shallow[0] and deep[1] > deep[0] and drill.is_monotonic_increasing):
        raise ValueError('Review the infographic statement')
    return (f'New wells moved to deep water: {shallow[0]:.1f} % of those started in 2005 to 2009 were in less than 100 m '
            f'of water, against {shallow[1]:.1f} % of those started in 2021 to 2025. Median drilling days rise with depth, '
            f'from {significant(drill.iloc[0])} d under 100 m to {significant(drill.iloc[-1])} d at 1,500 m and deeper.')


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


IMAGES = (['fig-map', 'fig-rig', 'pies-rig', 'fig-depth', 'pies-depth', 'days-overview-stage', 'days-overview-depth']
          + ['days-' + STAGES[a][0] for a in ACTIVITIES])


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


def build_html(out, cache, payload, stats, sources, audit, map_info, bundle=None):
    page = (ROOT / 'inputs' / 'page-template.html').read_text(encoding='utf-8')
    check = pd.read_csv(out / 'data' / 'repeat-key-sensitivity.csv')
    delta = (check.latest_key_median_days - check.median_days).abs().dropna()
    summary = f'{len(delta[delta.gt(0)])} of {len(delta)} comparable cell medians change. The largest absolute change is {significant(delta.max())} d.'
    page = page.replace('@@SENSITIVITY_RESULT@@', summary)
    holds = {'APDRawData.zip (file of 2 November 2026)': ('Application for Permit to Drill', 'file of 2 November 2026', 'permit type, requested spud date, water depth, rig name and rig type'),
             'eWellAPMRawData.zip': ('Application for Permit to Modify', '@@FILEDATE@@', 'operation codes and sub-operations, estimated operation days, status date and water depth'),
             'BoreholeRawData.zip': ('Boreholes', '@@FILEDATE@@', 'region, well-name suffix, spud and total-depth dates, status, water depth and surface location'),
             'APDRawData.zip': ('Application for Permit to Drill', '@@FILEDATE@@', 'column check only: neither table holds an estimated-days field')}
    source_list = ''.join('<li>' + holds[r.file][0] + ' (<a href="' + r.url + '">' + html.escape(r.file.split(' ')[0]) + '</a>), ' + holds[r.file][1].replace('@@FILEDATE@@', 'file of ' + page_date(r.file_date)) + ', downloaded ' + page_date(r.retrieved_utc) + ', SHA-256 <code>' + r.sha256 + '</code>: ' + holds[r.file][2] + '.</li>' for r in sources.itertuples() if r.file in holds)
    land = sources[sources.file.eq(LAND)].iloc[0]
    source_list += ('<li>Map land outline: Natural Earth 1:50m land (<a href="' + land.url + '">' + LAND + '</a>, version 5.1.2, public domain), downloaded '
                    + page_date(land.retrieved_utc) + ', SHA-256 <code>' + land.sha256 + '</code>.</li>')
    audit_rows = '<ul>' + ''.join('<li>' + html.escape(r.source + ': ' + r.rule.replace('_', ' ')) + ': ' + count_display(r.records) + ' records.</li>' for r in audit.itertuples()) + '</ul>'
    days_table(stats)  # fails closed if a selected record has no water depth
    page = page.replace('@@VERSIONS@@', versions()).replace('@@BUILD_COMMIT@@', BUILD_COMMIT).replace('@@BUILD_SHORT@@', BUILD_COMMIT[:8])
    page = page.replace('@@SOURCES@@', source_list).replace('@@AUDIT@@', audit_rows)
    page = page.replace('@@MAP_OBSERVATION@@', html.escape(map_observation(map_info['summary'])))
    page = page.replace('@@MAP_COUNTS@@', html.escape(map_footnote(map_info['summary'], map_info['audit'])))
    page = page.replace('@@IG_FOUND@@', html.escape(infographic_found(map_info['summary'], stats)))
    page = page.replace('@@IG_SCENE@@', scene_svg())
    for chart in payload:
        if chart['kind'] == 'pieset':
            page = page.replace('@@PIE_TOTALS_' + chart['id'].split('-')[1].upper() + '@@', pie_totals(chart))
    page = page.replace('@@CHECK_MAP@@', ' and '.join(f'{row.total:,} ({period})' for period, row in map_info['summary'].iterrows()))
    page = page.replace('@@LAND_DATE@@', page_date(land.retrieved_utc)).replace('@@LAND_URL@@', land.url)
    for token, activity in [('CHECK_COMPLETION', 'Completion'), ('CHECK_SPUD', RECORDED)]:
        values = stage_rows(stats, activity).median_days
        page = page.replace('@@' + token + '@@', ', '.join(significant(v) for v in values))
    page = page.replace('@@DAYS_PANELS@@', days_panels())
    page = page.replace('@@DAYS_DETAIL_TABLE@@', days_table(stats, detailed=True))
    page = page.replace('@@DAY_OBSERVATIONS@@', ''.join('<li>' + html.escape(b) + '</li>' for b in day_observations(out / 'data' / 'days-summary.csv')))
    for token, source in [('APM', 'eWellAPMRawData.zip'), ('BORE', 'BoreholeRawData.zip'), ('SCHEMA', 'APDRawData.zip')]:
        row = sources[sources.file.eq(source)].iloc[0]
        page = page.replace('@@' + token + '_DATE@@', page_date(row.retrieved_utc))
        page = page.replace('@@' + token + '_FILE@@', page_date(row.file_date))
    page = page.replace('@@CHART_DATA@@', json.dumps(payload, separators=(',', ':'), ensure_ascii=False).replace('<', '\\u003c'))
    for name in IMAGES:
        page = page.replace('@@IMAGE:' + name + '@@', 'data:image/png;base64,' + base64.b64encode(page_png(out / 'figures' / (name + '.png'))).decode())
    write_pages(out, cache, page, bundle)


def manifest():
    return json.loads((ROOT / 'inputs' / 'manifest.json').read_text(encoding='utf-8'))


def validate_inputs():
    """Every input, the revision 9 data files included, must match its pinned SHA-256."""
    for item in manifest():
        if sha(ROOT / item['path']) != item['sha256']:
            raise ValueError('Retained input hash mismatch: ' + item['path'])


def copy_reused(out):
    """Copy the pinned revision 9 data files, byte for byte, to data/ (the page links each one)."""
    pinned = {Path(i['path']).name for i in manifest()}
    for name in REUSED:
        if name + '.csv' not in pinned:
            raise ValueError('Reused data file is not pinned: ' + name)
        target = out / 'data' / (name + '.csv')
        if (ROOT / R9 / (name + '.csv')).resolve() != target.resolve():
            shutil.copyfile(ROOT / R9 / (name + '.csv'), target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'cache')
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--build-commit', required=True,
                        help='full 40-character SHA of the commit that holds this script, linked from Appendix A')
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
    wells, map_audit = read('map-wells'), read('map-selection')
    summary = read('map-summary').set_index('period')
    rig, depth = read('fig-p1-new-well-permits-by-rig-type'), read('new-well-permits-by-water-depth')
    if not rig.total.equals(depth.permits) or not rig.year.equals(depth.year):
        raise ValueError('Annual totals differ between the rig-type and water-depth files')
    matplotlib.rcParams.update({'svg.hashsalt': 'issue2-public-data-' + TAG, 'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    payload = ([map_figure(wells, land_rings(cache / LAND), out)] + count_figures(rig, depth, out)
               + overview_figures(stats, out) + days_figures(stats, out))
    build_html(out, cache, payload, stats, sources, audit, dict(summary=summary, audit=map_audit), args.bundle)
    print(overview_table(stats).to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
