"""Section 3 of the Issue 2 public data article, revision 10 ("Days from drilling to abandonment"), parked here for
the series' plugging-and-abandonment article.

The functions below are copied unchanged from ../issue2_public_data_r10/build_r10.py (commit 70c73f65). They draw
Figure 6 (median days of each stage, by water depth) and Figure 7 (days at each stage of a well's life) and write
the section 3.1 observations and Table B1 from data/days-summary.csv, which build_r9.py derived from the BSEE
borehole and APM files of 12 November 2026. Run:

    python days_charts.py --output-dir <folder>

The interactive versions of these charts are the interval, grouped and byband functions in days_charts.js.
"""
from __future__ import annotations

import argparse
import html
import math
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
TAG = 'pa-parked'
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
WC = ['#F0E442', '#2BB2A6', '#0072B2', '#0b3d5c']
EDGE = '#5a6b76'
INK = '#26323a'


def significant(value, digits=4):
    return format(float(value), f'.{digits}g') if value is not None and math.isfinite(float(value)) else 'Not available'


def count_display(value):
    rounded = float(significant(value))
    return ('≈' if rounded != value else '') + format(rounded, ',.0f')


def write_csv(frame, out, name):
    frame.to_csv(out / 'data' / (name + '.csv'), index=False, lineterminator='\n', float_format='%.12g')


def save_figure(fig, out, name):
    fig.savefig(out / 'figures' / (name + '.png'), dpi=150, metadata={'Software': TAG})
    fig.savefig(out / 'figures' / (name + '.svg'), metadata={'Date': None, 'Creator': TAG})
    svg = out / 'figures' / (name + '.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8', newline='\n')
    plt.close(fig)



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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, default=ROOT / 'data' / 'days-summary.csv')
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    out = args.output_dir.resolve()
    for folder in ['data', 'figures']:
        (out / folder).mkdir(parents=True, exist_ok=True)
    matplotlib.rcParams.update({'svg.hashsalt': 'issue2-public-data-' + TAG, 'font.family': 'DejaVu Sans', 'font.size': 10,
                                'axes.spines.top': False, 'axes.spines.right': False})
    stats = pd.read_csv(args.data)
    overview_figures(stats, out)
    days_figures(stats, out)
    (out / 'observations.txt').write_text('\n'.join(day_observations(args.data)) + '\n', encoding='utf-8', newline='\n')
    (out / 'table-b1.html').write_text(days_table(stats, detailed=True) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    main()
