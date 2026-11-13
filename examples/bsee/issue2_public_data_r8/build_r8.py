"""Rebuild the public-data page from pinned counts and a receipted cache."""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import math
import re
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent
BANDS = ['Under 100 m', '100 to 500 m', '500 to 1,500 m', '1,500 m and deeper']
ACTIVITIES = ['Completion', 'Intervention', 'Temporary abandonment',
              'Permanent abandonment', 'Spud to total depth']
RIGS = ['Jack-up', 'Drillship', 'Semisubmersible', 'DP semisubmersible',
        'Platform rig', 'Submersible', 'Other']
RC = ['#0b3d5c', '#2BB2A6', '#E69F00', '#56B4E9', '#CC79A7', '#D55E00', '#8a8985']
WC = ['#9cc8e2', '#4f9bcb', '#1f6aa5', '#0b3d5c']
WK = ['under_100_m', '100_to_500_m', '500_to_1500_m', '1500_m_and_deeper']
URL_BASE = 'https://www.data.bsee.gov/Well/Files/'
FILES = {n: URL_BASE + n for n in ['APDRawData.zip', 'eWellAPMRawData.zip', 'BoreholeRawData.zip']}
FILES['plotly-2.35.2.min.js'] = 'https://cdn.plot.ly/plotly-2.35.2.min.js'
OLD_SHA = 'b4ab66063de5a95c78d0e4d33d220ea806ef07f114bd2add6efa9e8561d299c0'

def significant(value, digits=4):
    return format(float(value), f'.{digits}g') if value is not None and math.isfinite(float(value)) else 'Not available'

def count_display(value):
    rounded = float(significant(value))
    return ('≈' if rounded != value else '') + format(rounded, ',.0f')

def band_from_feet(value):
    try:
        metres = float(value) * .3048
    except (ValueError, TypeError):
        return 'Missing depth'
    return BANDS[sum(metres >= e for e in [100, 500, 1500])] if math.isfinite(metres) and metres >= 0 else 'Missing depth'

def pie_years(years):
    if not {2005, 2015, 2025}.issubset(set(years)):
        raise ValueError('Missing fixed representative full year')
    return [2005, 2015, 2025]

def classify_operation(code, subcodes):
    if 'PLUGBACK' in subcodes or code in {'SIDETRACK', 'BYPASS', 'DEEPEN'}:
        return 'Excluded: new hole'
    if code == 'ABANDON':
        return ('Permanent abandonment' if 'PERMABAN' in subcodes else
                'Temporary abandonment' if 'TEMPABAN' in subcodes else 'Excluded: unspecified abandonment')
    if code in {'WORKOVER', 'ENHANCE'} or (code == 'COMP' and 'ZONE' in subcodes):
        return 'Intervention'
    if code == 'COMP':
        return 'Completion'
    if code in {'OTHER', 'INFORM', 'UTIL'}:
        return 'Excluded: other or administrative scope'
    raise ValueError(f'Unmapped primary operation: {code}')

def unique_records(frame, key):
    result = frame.drop_duplicates().copy()
    if result[key].eq('').any() or result[key].duplicated().any():
        raise ValueError(f'Missing or conflicting records for {key}')
    return result.sort_values(key, kind='stable').reset_index(drop=True)

def dates(values):
    full = pd.to_datetime(values, errors='coerce', format='%m/%d/%Y %I:%M:%S %p')
    return full.fillna(pd.to_datetime(values, errors='coerce', format='%m/%d/%Y'))

def prepare_boreholes(bore):
    b = unique_records(bore, 'API_WELL_NUMBER')
    audit = {'raw_records': len(bore), 'duplicate_rows': len(bore) - len(b)}
    gulf = b.REGION_CODE.eq('G')
    original = b.WELL_NAME_SUFFIX.eq('ST00BP00')
    cancelled = b.BOREHOLE_STAT_CD.eq('CNL')
    audit.update(non_gulf=int((~gulf).sum()), non_original=int((gulf & ~original).sum()),
                 cancelled=int((gulf & original & cancelled).sum()))
    b = b[gulf & original & ~cancelled].copy()
    spud, td = dates(b.WELL_SPUD_DATE), dates(b.TOTAL_DEPTH_DATE)
    audit['missing_spud_date'] = int(spud.isna().sum())
    audit['invalid_nonblank_spud_date'] = int((spud.isna() & b.WELL_SPUD_DATE.ne('')).sum())
    audit['outside_years'] = int((spud.notna() & ~spud.dt.year.between(2005, 2025)).sum())
    b['days'] = (td - spud).dt.total_seconds() / 86400
    b['band'] = b.WATER_DEPTH.map(band_from_feet)
    b['activity'] = 'Spud to total depth'
    b = b[spud.dt.year.between(2005, 2025)]
    audit['zero_depth_selected'] = int(pd.to_numeric(b.WATER_DEPTH, errors='coerce').eq(0).sum())
    audit.update(blank_td_selected=int(b.TOTAL_DEPTH_DATE.eq('').sum()),
        invalid_nonblank_td_selected=int((dates(b.TOTAL_DEPTH_DATE).isna() & b.TOTAL_DEPTH_DATE.ne('')).sum()),
        zero_interval_selected=int(b.days.eq(0).sum()), negative_interval_selected=int(b.days.lt(0).sum()))
    return b[['activity', 'band', 'days']], audit

def prepare_apm(apm, sub, bore):
    fields = ['SN_APM', 'API_WELL_NUMBER', 'ACC_STATUS_DATE', 'APM_OP_CD', 'EST_OPERATION_DAYS', 'WATER_DEPTH']
    a = unique_records(apm[fields], 'SN_APM')
    audit = {'raw_records': len(apm), 'duplicate_rows': len(apm) - len(a)}
    regions = bore.groupby('API_WELL_NUMBER').REGION_CODE.agg(lambda s: s.iloc[0] if s.nunique() == 1 else '')
    region = a.API_WELL_NUMBER.map(regions)
    audit['unmatched_or_ambiguous_region'] = int((region.isna() | region.eq('')).sum())
    audit['non_gulf'] = int((region.notna() & ~region.isin(['G', ''])).sum())
    a = a[region.eq('G')].copy()
    year = dates(a.ACC_STATUS_DATE).dt.year
    audit['missing_status_date'] = int(year.isna().sum())
    audit['invalid_nonblank_status_date'] = int((year.isna() & a.ACC_STATUS_DATE.ne('')).sum())
    audit['outside_years'] = int((year.notna() & ~year.between(2005, 2025)).sum())
    a = a[year.between(2005, 2025)].copy()
    audit['repeat_api_operation_year_extra_submissions'] = int(a.assign(year=year.loc[a.index]).duplicated(['API_WELL_NUMBER', 'APM_OP_CD', 'year']).sum())
    subcodes = sub.groupby('SN_APM_FK').APM_SUBOP_CD.agg(set).to_dict()
    a['activity'] = [classify_operation(r.APM_OP_CD, subcodes.get(r.SN_APM, set())) for r in a.itertuples()]
    a['band'] = a.WATER_DEPTH.map(band_from_feet)
    a['days'] = pd.to_numeric(a.EST_OPERATION_DAYS, errors='coerce')
    for label, n in a.activity.value_counts().items():
        audit[label] = int(n)
    events = a[a.activity.isin(ACTIVITIES)][['activity', 'band', 'days']].copy()
    audit['zero_depth_included'] = int(pd.to_numeric(a.loc[events.index, 'WATER_DEPTH'], errors='coerce').eq(0).sum())
    cross = pd.DataFrame([dict(activity=r.activity, primary=r.APM_OP_CD, subtype=c) for r in a.itertuples() for c in sorted(subcodes.get(r.SN_APM, set()) or {'(none)'})])
    events.attrs['subtype_activity'] = cross.groupby(['activity', 'primary', 'subtype']).size().rename('submissions').reset_index()
    events.attrs['sensitivity'] = latest_key_sensitivity(a)
    return events, audit

def summarize_days(events):
    rows = []
    for activity in ACTIVITIES:
        for band in BANDS + ['Missing depth']:
            g = events[events.activity.eq(activity) & events.band.eq(band)]
            days = pd.to_numeric(g.days, errors='coerce')
            finite = days.notna() & days.abs().lt(float('inf'))
            good = days[finite & days.gt(0)]
            rows.append(dict(activity=activity, band=band, records=len(g), n=len(good),
                missing_invalid_days=int((~finite).sum()), nonpositive_days=int((finite & days.le(0)).sum()),
                excluded_days=len(g)-len(good), q1_days=good.quantile(.25),
                median_days=good.median(), q3_days=good.quantile(.75)))
    return pd.DataFrame(rows)


def latest_key_sensitivity(frame):
    a = frame.assign(status_date=dates(frame.ACC_STATUS_DATE))
    a['status_year'] = a.status_date.dt.year
    latest = a.sort_values(['status_date', 'SN_APM'], kind='stable').drop_duplicates(
        ['API_WELL_NUMBER', 'APM_OP_CD', 'status_year'], keep='last')
    keys = ['activity', 'band']
    base = summarize_days(a)[keys + ['n', 'median_days']]
    check = summarize_days(latest)[keys + ['n', 'median_days']].rename(
        columns={'n': 'latest_key_n', 'median_days': 'latest_key_median_days'})
    result = base.merge(check, on=keys, validate='one_to_one')
    return result[result.activity.ne('Spud to total depth') & result.band.isin(BANDS)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cache_source(cache, name, url, offline, expected_sha=None):
    path = cache / name
    receipt = path.with_suffix('.receipt.json')
    if not path.exists():
        if offline:
            raise FileNotFoundError(f'Offline cache missing: {name}')
        with urllib.request.urlopen(url, timeout=600) as response:
            content = response.read()
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


def read_table(cache, archive, member, headers):
    with zipfile.ZipFile(cache / archive) as z:
        name, = [n for n in z.namelist() if Path(n).name == member + '.txt']
        with z.open(name) as stream:
            frame = pd.read_csv(stream, dtype=str, keep_default_na=False, encoding='cp1252')
    print(f'{archive}/{member}: ' + ', '.join(frame.columns), flush=True)
    headers.extend(dict(file=archive, member=member, column=c) for c in frame.columns)
    return frame.apply(lambda s: s.str.strip())


def archive_members(cache):
    rows = []
    for name in FILES:
        if name.endswith('.zip'):
            with zipfile.ZipFile(cache / name) as z:
                names = sorted(z.namelist())
            if name == 'APDRawData.zip' and {Path(n).name for n in names if n.endswith('.txt')} != {'mv_apddata_all.txt', 'mv_apd_main_all.txt'}:
                raise ValueError('APD data-member set changed')
            rows.extend(dict(file=name, member=n) for n in names)
    return pd.DataFrame(rows)


def write_csv(frame, out, name):
    frame.to_csv(out / 'data' / (name + '.csv'), index=False, lineterminator='\n', float_format='%.12g')


def mapping_table(primary, sub):
    rules = {'ABANDON': 'PERMABAN before TEMPABAN; unspecified excluded',
        'COMP': 'ZONE -> intervention; otherwise completion', 'WORKOVER': 'Intervention',
        'ENHANCE': 'Intervention', 'OTHER': 'Excluded: ambiguous scope',
        'INFORM': 'Excluded: administrative scope', 'UTIL': 'Excluded: utility scope'}
    p = primary.assign(level='primary', rule=primary.VALUE.map(rules))
    if p.rule.isna().any():
        raise ValueError('Unmapped primary code dictionary')
    s = sub.assign(level='subtype', rule='Retain primary classification')
    for code, rule in {'PLUGBACK': 'Exclude new-hole work before any other rule',
        'PERMABAN': 'ABANDON -> permanent; precedence over TEMPABAN',
        'TEMPABAN': 'ABANDON -> temporary unless PERMABAN',
        'ZONE': 'COMP -> intervention'}.items():
        s.loc[s.VALUE.eq(code), 'rule'] = rule
    return pd.concat([p, s], ignore_index=True)[['level', 'VALUE', 'DESCRIP', 'rule']]


def save_figure(fig, out, name):
    fig.savefig(out / 'figures' / (name + '.png'), dpi=150, metadata={'Software': 'r8'})
    fig.savefig(out / 'figures' / (name + '.svg'), metadata={'Date': None, 'Creator': 'r8'})
    svg = out / 'figures' / (name + '.svg')
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text(encoding='utf-8').splitlines()) + '\n', encoding='utf-8', newline='\n')
    plt.close(fig)


def count_figures(rig, depth, out):
    payload = []
    for frame, keys, labels, colours, kind in [(rig, RIGS, RIGS, RC, 'rig'), (depth, WK, BANDS, WC, 'depth')]:
        fig, ax = plt.subplots(figsize=(11, 4.8), layout='constrained')
        bottom = pd.Series(0, index=frame.index)
        for key, label, colour in zip(keys, labels, colours):
            ax.bar(frame.year, frame[key], bottom=bottom, label=label, color=colour)
            bottom += frame[key]
        ax.set(xlabel='Year of requested spud date', ylabel='New-well permits (-)')
        ax.legend(ncol=3, fontsize=8, loc='upper right')
        save_figure(fig, out, 'fig-' + kind)
        payload.append(dict(id='fig-' + kind, kind='bar', rows=frame.to_dict('records'), keys=keys, labels=labels, colours=colours))
        pie_rows = []
        for year in pie_years(frame.year):
            row = frame[frame.year.eq(year)].iloc[0]
            values = [int(row[k]) for k in keys]
            total = sum(values)
            pie_rows.extend(dict(year=year, category=l, permits=v, total=total, share_percent=v / total * 100) for l, v in zip(labels, values))
            shown = [(v, l, c) for v, l, c in zip(values, labels, colours) if v > 0]
            values, pie_labels, pie_colours = map(list, zip(*shown))
            shares = [f'{v / total * 100:.1f}%' for v in values]
            fig, ax = plt.subplots(figsize=(6, 5.2), layout='constrained')
            share_labels = iter(shares)
            wedges, _, _ = ax.pie(values, colors=pie_colours, startangle=90,
                autopct=lambda p: (lambda text: text if p >= 5 else '')(next(share_labels)), pctdistance=.75,
                textprops={'fontsize': 8}, wedgeprops={'edgecolor': 'white'})
            ax.legend(wedges, [f'{l}: {s}' for l, s in zip(pie_labels, shares)], loc='lower center', bbox_to_anchor=(.5, -.16), ncol=2, fontsize=8)
            ax.set_title(f'{year}: {total} permits')
            name = f'pie-{kind}-{year}'
            save_figure(fig, out, name)
            payload.append(dict(id=name, kind='pie', values=values, labels=pie_labels, colours=pie_colours, year=year, total=total, shares=shares))
        write_csv(pd.DataFrame(pie_rows), out, 'pies-' + kind)
    return payload


def days_figure(stats, out):
    fig, axes = plt.subplots(5, 1, figsize=(8, 14), layout='constrained')
    for ax, activity in zip(axes, ACTIVITIES):
        rows = stats[(stats.activity == activity) & stats.band.isin(BANDS)].set_index('band').loc[BANDS]
        for i, (_, row) in enumerate(rows.iterrows()):
            if row.n:
                ax.plot([row.q1_days, row.q3_days], [i, i], color=WC[i], linewidth=3)
                ax.plot(row.median_days, i, 'o', color=WC[i])
                ax.annotate('n' + (' ' if count_display(row.n).startswith('≈') else '=') + count_display(row.n), (row.q3_days, i), xytext=(5, 5), textcoords='offset points', fontsize=8)
        ax.set_title(activity + (' (recorded interval)' if activity == ACTIVITIES[-1] else ' (estimate)'), fontsize=11)
        ax.set(xlabel='Days (d)', yticks=range(4), yticklabels=BANDS, xlim=(0, max(1, rows.q3_days.max()) * 1.6))
        ax.grid(axis='x', alpha=.2)
        ax.invert_yaxis()
    save_figure(fig, out, 'fig-days')


def day_observations(csv_path):
    stats = pd.read_csv(csv_path).set_index(['activity', 'band'])
    medians = {a: stats.loc[a].loc[BANDS, 'median_days'] for a in ACTIVITIES}
    bullets = []
    for activity, label in [('Completion', 'Completion estimate'), ('Spud to total depth', 'Recorded spud-to-total-depth')]:
        values = medians[activity]
        if not values.map(math.isfinite).all() or not values.is_monotonic_increasing or values.iloc[0] >= values.iloc[-1]:
            raise ValueError('Review rising-median observation: ' + activity)
        bullets.append(f'{label} medians rise with water depth, from {significant(values.iloc[0])} d under 100 m to {significant(values.iloc[-1])} d at 1,500 m and deeper.')
    if not all(medians[a].map(math.isfinite).all() for a in ['Intervention', 'Permanent abandonment']):
        raise ValueError('Range observation requires medians for all four depth bands')
    ranges = [f'{significant(medians[a].min())} to {significant(medians[a].max())}' for a in ['Intervention', 'Permanent abandonment']]
    bullets.append(f'Across the four depth bands, intervention estimate medians range from {ranges[0]} d; permanent-abandonment estimate medians range from {ranges[1]} d.')
    return bullets


def page_date(value):
    date = datetime.fromisoformat(value[:10])
    return f'{date.day} {date.strftime("%B %Y")}'


def days_table(stats, detailed=False):
    columns = ['Activity and basis', 'Water depth', 'Used (-)', 'Q1 (d)', 'Median (d)', 'Q3 (d)']
    if detailed:
        columns[2:3] = ['Records (-)', 'Used (-)', 'Missing/invalid (-)', 'Nonpositive (-)']
    else:
        if stats.loc[~stats.band.isin(BANDS), 'records'].sum():
            raise ValueError('Selected records have missing depth; review the page statement')
        stats = stats[stats.band.isin(BANDS)]
    rows = []
    for row in stats.itertuples():
        basis = 'recorded interval' if row.activity == ACTIVITIES[-1] else 'estimate'
        counts = [row.records, row.n, row.missing_invalid_days, row.nonpositive_days] if detailed else [row.n]
        values = [row.activity + ' (' + basis + ')', row.band] + [count_display(v) for v in counts] + [significant(v) for v in [row.q1_days, row.median_days, row.q3_days]]
        rows.append('<tr>' + ''.join('<td>' + html.escape(v) + '</td>' for v in values) + '</tr>')
    return '<div class="nl-tablewrap days-table"><table><thead><tr>' + ''.join('<th scope="col">' + c + '</th>' for c in columns) + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>'


def build_html(out, cache, payload, stats, sources, audit):
    page = (ROOT / 'inputs' / 'page-template.html').read_text(encoding='utf-8')
    check = pd.read_csv(out / 'data' / 'repeat-key-sensitivity.csv')
    delta = (check.latest_key_median_days - check.median_days).abs().dropna()
    summary = f'{len(delta[delta.gt(0)])} of {len(delta)} comparable cell medians change. The largest absolute change is {significant(delta.max())} d.'
    page = page.replace('@@SENSITIVITY_RESULT@@', summary)
    holds = {'APDRawData.zip (file of 2 November 2026)': ('Application for Permit to Drill', 'file of 2 November 2026', 'permit type, requested spud date, water depth, rig name and rig type'),
             'eWellAPMRawData.zip': ('Application for Permit to Modify', 'file of 12 November 2026', 'operation codes and sub-operations, estimated operation days, status date and water depth'),
             'BoreholeRawData.zip': ('Boreholes', 'file of 12 November 2026', 'region, well-name suffix, spud and total-depth dates, status and water depth')}
    source_list = ''.join('<li>' + holds[r.file][0] + ' (<a href="' + r.url + '">' + html.escape(r.file.split(' ')[0]) + '</a>), ' + holds[r.file][1] + ', downloaded ' + page_date(r.retrieved_utc) + ', SHA-256 <code>' + r.sha256 + '</code>: ' + holds[r.file][2] + '.</li>' for r in sources.itertuples() if r.file in holds)
    audit_rows = '<ul>' + ''.join('<li>' + html.escape(r.source + ': ' + r.rule.replace('_', ' ')) + ' — ' + count_display(r.records) + ' records.</li>' for r in audit.itertuples()) + '</ul>'
    days_table(stats)  # fails closed if a selected record has no water depth
    page = page.replace('@@SOURCES@@', source_list).replace('@@AUDIT@@', audit_rows)
    for token, activity in [('CHECK_COMPLETION', 'Completion'), ('CHECK_SPUD', 'Spud to total depth')]:
        values = stats[stats.activity.eq(activity) & stats.band.isin(BANDS)].set_index('band').loc[BANDS, 'median_days']
        page = page.replace('@@' + token + '@@', ', '.join(significant(v) for v in values))
    page = page.replace('@@DAYS_DETAIL_TABLE@@', days_table(stats, detailed=True))
    page = page.replace('@@DAY_OBSERVATIONS@@', ''.join('<li>' + html.escape(b) + '</li>' for b in day_observations(out / 'data' / 'days-summary.csv')))
    for token, source in [('APM', 'eWellAPMRawData.zip'), ('BORE', 'BoreholeRawData.zip'), ('SCHEMA', 'APDRawData.zip')]:
        date = page_date(sources.loc[sources.file.eq(source), 'retrieved_utc'].iloc[0])
        page = page.replace('@@' + token + '_DATE@@', date)
    page = page.replace('@@CHART_DATA@@', json.dumps(payload, separators=(',', ':')).replace('<', '\\u003c'))
    for name in ['fig-rig', 'fig-depth', 'fig-days'] + [f'pie-{k}-{y}' for k in ['rig', 'depth'] for y in [2005, 2015, 2025]]:
        page = page.replace('@@IMAGE:' + name + '@@', 'data:image/png;base64,' + base64.b64encode((out / 'figures' / (name + '.png')).read_bytes()).decode())
    library = (cache / 'plotly-2.35.2.min.js').read_text(encoding='utf-8')
    if '</script' in library.lower():
        raise ValueError('Unexpected script closing tag in library')
    if re.search(r'@@[^@\s]+@@', page.replace('@@PLOTLY_LIBRARY@@', '')):
        raise ValueError('Unresolved page token')
    page = page.replace('@@PLOTLY_LIBRARY@@', library)
    (out / 'issue2-public-data-r8.html').write_text(page, encoding='utf-8', newline='\n')


def validate_inputs():
    for item in json.loads((ROOT / 'inputs' / 'manifest.json').read_text(encoding='utf-8')):
        if sha(ROOT / 'inputs' / item['file']) != item['sha256']:
            raise ValueError('Retained input hash mismatch: ' + item['file'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'cache')
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args(argv)
    out, cache = args.output_dir.resolve(), args.data_dir.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    for folder in ['data', 'figures']:
        (out / folder).mkdir(parents=True, exist_ok=True)
    validate_inputs()
    pins = json.loads((ROOT / 'inputs' / 'source-pins.json').read_text(encoding='utf-8'))
    records = [cache_source(cache, n, u, args.offline, pins[n]) for n, u in FILES.items()]
    for record in records:
        record['role'] = 'Column check of the permit file' if record['file'] == 'APDRawData.zip' else 'Offline chart library' if record['file'].endswith('.js') else 'Duration analysis'
    records.insert(0, dict(file='APDRawData.zip (file of 2 November 2026)', url=URL_BASE+'APDRawData.zip', retrieved_utc='2026-11-03T02:28Z', sha256=OLD_SHA, role='Counts for Figures 1 and 2 and Table 1'))
    sources, headers = pd.DataFrame(records), []
    for member in ['mv_apddata_all', 'mv_apd_main_all']:
        apd = read_table(cache, 'APDRawData.zip', member, headers)
        if any(re.search('DAY|DUR', c) for c in apd.columns):
            raise ValueError('APD days schema changed; review the page statement')
    bore = read_table(cache, 'BoreholeRawData.zip', 'mv_boreholes_all', headers)
    apm, sub, primary, subdefs = [read_table(cache, 'eWellAPMRawData.zip', n, headers) for n in
        ['mv_apm_main', 'mv_apm_suboperations', 'mv_apm_primary_op_codes', 'mv_apm_suboperation_codes']]
    a, aa = prepare_apm(apm, sub, bore)
    write_csv(a.attrs.pop('subtype_activity'), out, 'subtype-activity')
    write_csv(a.attrs.pop('sensitivity'), out, 'repeat-key-sensitivity')
    write_csv(archive_members(cache), out, 'source-members')
    b, ba = prepare_boreholes(bore)
    stats = summarize_days(pd.concat([a, b], ignore_index=True))
    audit = pd.DataFrame([dict(source=s, rule=k, records=v) for s, d in [('APM', aa), ('Borehole', ba)] for k, v in d.items()])
    for frame, name in [(sources, 'sources'), (pd.DataFrame(headers), 'source_columns'), (mapping_table(primary, subdefs), 'code_mapping'), (stats, 'days-summary'), (audit, 'exclusions')]:
        write_csv(frame, out, name)
    rig, depth, table = [pd.read_csv(ROOT / 'inputs' / n) for n in ['fig-p1-new-well-permits-by-rig-type.csv', 'new-well-permits-by-water-depth.csv', 'table1.csv']]
    if not rig.total.equals(depth.permits) or not rig.year.equals(depth.year):
        raise ValueError('Annual totals differ between the rig-type and water-depth files')
    for frame, name in [(rig, 'fig-p1-new-well-permits-by-rig-type'), (depth, 'new-well-permits-by-water-depth'), (table, 'table1')]:
        write_csv(frame, out, name)
    matplotlib.rcParams.update({'svg.hashsalt': 'issue2-public-data-r8', 'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    payload = count_figures(rig, depth, out)
    days_figure(stats, out)
    build_html(out, cache, payload, stats, sources, audit)
    print(stats.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
