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
TAG = 'r9'
PAGE = 'issue2-public-data-r9.html'
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
RC = ['#0b3d5c', '#2BB2A6', '#E69F00', '#56B4E9', '#CC79A7', '#D55E00', '#8a8985']
WC = ['#9cc8e2', '#4f9bcb', '#1f6aa5', '#0b3d5c']
WK = ['under_100_m', '100_to_500_m', '500_to_1500_m', '1500_m_and_deeper']
PIE_YEARS = [2005, 2015, 2025]
MAP_PERIODS = [(2005, 2009), (2021, 2025)]
MAP_BOX = (-98.0, -80.0, 18.0, 31.0)       # lon min, lon max, lat min, lat max shown
CLAMP_BOX = (-101.0, -77.0, 15.0, 34.0)    # land rings are clamped to this larger box
LAND = 'ne_50m_land.geojson'
NE_COMMIT = 'f1890d9f152c896d250a77557a5751a93d494776'  # natural-earth-vector tag v5.1.2
URL_BASE = 'https://www.data.bsee.gov/Well/Files/'
FILES = {n: URL_BASE + n for n in ['APDRawData.zip', 'eWellAPMRawData.zip', 'BoreholeRawData.zip']}
FILES['plotly-2.35.2.min.js'] = 'https://cdn.plot.ly/plotly-2.35.2.min.js'
FILES[LAND] = f'https://raw.githubusercontent.com/nvkelso/natural-earth-vector/{NE_COMMIT}/geojson/{LAND}'
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
    if not set(PIE_YEARS).issubset(set(years)):
        raise ValueError('Missing fixed representative full year')
    return list(PIE_YEARS)


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


def original_gulf_boreholes(bore):
    b = unique_records(bore, 'API_WELL_NUMBER')
    audit = {'raw_records': len(bore), 'duplicate_rows': len(bore) - len(b)}
    gulf = b.REGION_CODE.eq('G')
    original = b.WELL_NAME_SUFFIX.eq('ST00BP00')
    cancelled = b.BOREHOLE_STAT_CD.eq('CNL')
    audit.update(non_gulf=int((~gulf).sum()), non_original=int((gulf & ~original).sum()),
                 cancelled=int((gulf & original & cancelled).sum()))
    return b[gulf & original & ~cancelled].copy(), audit


def prepare_boreholes(bore):
    b, audit = original_gulf_boreholes(bore)
    spud, td = dates(b.WELL_SPUD_DATE), dates(b.TOTAL_DEPTH_DATE)
    audit['missing_spud_date'] = int(spud.isna().sum())
    audit['invalid_nonblank_spud_date'] = int((spud.isna() & b.WELL_SPUD_DATE.ne('')).sum())
    audit['outside_years'] = int((spud.notna() & ~spud.dt.year.between(2005, 2025)).sum())
    b['days'] = (td - spud).dt.total_seconds() / 86400
    b['band'] = b.WATER_DEPTH.map(band_from_feet)
    b['activity'] = RECORDED
    b = b[spud.dt.year.between(2005, 2025)]
    audit['zero_depth_selected'] = int(pd.to_numeric(b.WATER_DEPTH, errors='coerce').eq(0).sum())
    audit.update(blank_td_selected=int(b.TOTAL_DEPTH_DATE.eq('').sum()),
        invalid_nonblank_td_selected=int((dates(b.TOTAL_DEPTH_DATE).isna() & b.TOTAL_DEPTH_DATE.ne('')).sum()),
        zero_interval_selected=int(b.days.eq(0).sum()), negative_interval_selected=int(b.days.lt(0).sum()))
    return b[['activity', 'band', 'days']], audit


def map_wells(bore):
    """Surface locations of original Gulf boreholes spudded in the two map periods."""
    b, _ = original_gulf_boreholes(bore)
    year = dates(b.WELL_SPUD_DATE).dt.year
    lat = pd.to_numeric(b.SURF_LATITUDE, errors='coerce')
    lon = pd.to_numeric(b.SURF_LONGITUDE, errors='coerce')
    rows, audit = [], []
    for start, end in MAP_PERIODS:
        period = f'{start} to {end}'
        pick = year.between(start, end)
        lo, la = MAP_BOX[:2], MAP_BOX[2:]
        good = pick & lat.between(*la) & lon.between(*lo)
        audit.append(dict(period=period, selected=int(pick.sum()), mapped=int(good.sum()),
                          missing_or_outside_coordinates=int((pick & ~good).sum())))
        part = b[good]
        rows.append(pd.DataFrame({'period': period, 'spud_year': year[good].astype(int),
            'api_well_number': part.API_WELL_NUMBER, 'latitude': lat[good], 'longitude': lon[good],
            'water_depth_m': pd.to_numeric(part.WATER_DEPTH, errors='coerce') * .3048,
            'band': part.WATER_DEPTH.map(band_from_feet)}))
    wells = pd.concat(rows, ignore_index=True).sort_values(['period', 'api_well_number'], kind='stable').reset_index(drop=True)
    if wells.band.eq('Missing depth').any():
        raise ValueError('Mapped well with missing water depth; review the map legend')
    return wells, pd.DataFrame(audit)


def map_summary(wells):
    table = wells.groupby(['period', 'band']).size().unstack(fill_value=0).reindex(columns=BANDS, fill_value=0)
    table['total'] = table.sum(axis=1)
    return table.reindex([f'{a} to {b}' for a, b in MAP_PERIODS])


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
    return result[result.activity.ne(RECORDED) & result.band.isin(BANDS)]


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


def archive_date(path):
    """Publication date of a BSEE archive: the newest date stamp on its data members."""
    with zipfile.ZipFile(path) as z:
        stamps = {i.date_time[:3] for i in z.infolist() if i.filename.endswith('.txt')}
    if not stamps:
        raise ValueError('No dated data member in ' + path.name)
    return '%04d-%02d-%02d' % max(stamps)


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
            ax.scatter(p.longitude, p.latitude, s=7, color=colour, label=band, edgecolors='none', zorder=2)
        ax.text(*MAP_LABELS[0][:2], MAP_LABELS[0][2], ha='center', va='center', fontsize=9, color='#4f6d7a', style='italic')
        ax.set(xlim=MAP_BOX[:2], ylim=MAP_BOX[2:], xlabel='Longitude (°)', ylabel='Latitude (°)')
        ax.set_aspect(aspect)
        ax.set_facecolor('#f4f8fb')
        ax.set_title(period, fontsize=11)
    handles = [plt.Line2D([], [], marker='o', linestyle='', color=c, label=b) for b, c in zip(BANDS, WC)]
    fig.legend(handles=handles, loc='outside upper center', ncol=4, fontsize=9, title='Water depth')
    save_figure(fig, out, 'fig-map')
    traces = []
    for i, period in enumerate(periods):
        part = wells[wells.period.eq(period)]
        for band, colour in zip(BANDS, WC):
            p = part[part.band.eq(band)]
            traces.append(dict(axis=i, band=band, colour=colour, lon=[round(v, 4) for v in p.longitude],
                lat=[round(v, 4) for v in p.latitude], depth=[round(v) for v in p.water_depth_m], year=[int(v) for v in p.spud_year]))
    return dict(id='fig-map', kind='map', periods=periods, box=MAP_BOX, aspect=aspect, bands=BANDS,
                land=[[list(pt) for pt in ring] for ring in rings], traces=traces, labels=MAP_LABELS)


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
        label_shares(ax, wedges, pie_labels, values, shares, total)
        ax.set_title(str(year), fontsize=12)
        pies.append(dict(year=year, total=total, values=values, labels=pie_labels, colours=pie_colours, shares=shares,
                         small=small_share_lines(pie_labels, values, shares, total)))
    used = [(l, c) for l, c in zip(labels, colours) if any(l in p['labels'] for p in pies)]
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for _, c in used]
    fig.legend(handles, [l for l, _ in used], loc='outside lower center', ncol=len(used), fontsize=9)
    name = 'pies-' + kind
    save_figure(fig, out, name)
    write_csv(pd.DataFrame(pie_rows), out, name)
    return dict(id=name, kind='pieset', pies=pies)


def small_share_lines(labels, values, shares, total, per_line=2):
    """Shares under 5 % as short lines printed under the pie, so no label is lost or overlaps."""
    small = [f'{l} {s}' for l, v, s in zip(labels, values, shares) if v / total * 100 < 5]
    return ['Under 5%:'] + ['; '.join(small[i:i + per_line]) for i in range(0, len(small), per_line)] if small else []


def label_shares(ax, wedges, labels, values, shares, total):
    """Every share is printed: inside the slice for 5 % or more, in a list under the pie below 5 %."""
    for wedge, value, share in zip(wedges, values, shares):
        if value / total * 100 >= 5:
            angle = math.radians((wedge.theta1 + wedge.theta2) / 2)
            ax.text(.68 * math.cos(angle), .68 * math.sin(angle), share, ha='center', va='center', fontsize=9, color='white')
    lines = small_share_lines(labels, values, shares, total)
    if lines:
        ax.text(0, -1.12, '\n'.join(lines), ha='center', va='top', fontsize=8.5, color='#333333')


def pie_totals(pieset):
    return ', '.join(f"{p['total']:,} in {p['year']}" for p in pieset['pies'])


def stage_rows(stats, activity):
    return stats[(stats.activity == activity) & stats.band.isin(BANDS)].set_index('band').loc[BANDS]


def days_figures(stats, out):
    """One small interval chart per stage of well life, in life order."""
    payload = []
    for activity in ACTIVITIES:
        slug, _, _ = STAGES[activity]
        rows = stage_rows(stats, activity)
        fig, ax = plt.subplots(figsize=(8, 2.7), layout='constrained')
        for i, (_, row) in enumerate(rows.iterrows()):
            if row.n:
                ax.plot([row.q1_days, row.q3_days], [i, i], color=WC[i], linewidth=3)
                ax.plot(row.median_days, i, 'o', color=WC[i], markeredgecolor='#0b3d5c')
                ax.annotate(count_label(row.n), (row.q3_days, i), xytext=(5, -3), textcoords='offset points', fontsize=8)
        ax.set(xlabel='Days (d)', yticks=range(4), yticklabels=BANDS, xlim=(0, max(1, rows.q3_days.max()) * 1.35))
        ax.grid(axis='x', alpha=.2)
        ax.invert_yaxis()
        save_figure(fig, out, 'days-' + slug)
        payload.append(dict(id='days-' + slug, kind='interval', bands=BANDS, colours=WC,
            q1=[none_if_nan(v) for v in rows.q1_days], median=[none_if_nan(v) for v in rows.median_days],
            q3=[none_if_nan(v) for v in rows.q3_days], n=[int(v) for v in rows.n],
            nlabel=[count_label(v) for v in rows.n],
            shown=[[significant(v) for v in (r.q1_days, r.median_days, r.q3_days)] for r in rows.itertuples()]))
    return payload


def none_if_nan(value):
    return None if value is None or not math.isfinite(float(value)) else float(value)


def count_label(n):
    shown = count_display(n)
    return 'n' + (' ' if shown.startswith('≈') else '=') + shown


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
    """The five stage charts of Figure 6, each labelled by its stage only."""
    parts = []
    for letter, activity in zip('abcde', ACTIVITIES):
        slug, name, basis = STAGES[activity]
        alt = f'{name}: median and quartile days by water-depth band'
        parts.append(f'<div class="stage"><p class="stage-label">{letter}. {name} <span class="basis">({basis})</span></p>'
                     f'<div id="days-{slug}" class="viz" style="height:230px" role="img" aria-label="{alt}"></div>'
                     f'<img class="chart-fallback" data-for="days-{slug}" src="@@IMAGE:days-{slug}@@" alt="{alt}"></div>')
    return ''.join(parts)


BUILD_COMMIT = 'dashwork/issue2-public-data-r8'  # replaced by --build-commit: the commit that holds this script


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


IMAGES = ['fig-map', 'fig-rig', 'pies-rig', 'fig-depth', 'pies-depth'] + ['days-' + STAGES[a][0] for a in ACTIVITIES]


def build_html(out, cache, payload, stats, sources, audit, map_info):
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
        page = page.replace('@@IMAGE:' + name + '@@', 'data:image/png;base64,' + base64.b64encode((out / 'figures' / (name + '.png')).read_bytes()).decode())
    library = (cache / 'plotly-2.35.2.min.js').read_text(encoding='utf-8')
    if '</script' in library.lower():
        raise ValueError('Unexpected script closing tag in library')
    if re.search(r'@@[^@\s]+@@', page.replace('@@PLOTLY_LIBRARY@@', '')):
        raise ValueError('Unresolved page token')
    page = page.replace('@@PLOTLY_LIBRARY@@', library)
    (out / PAGE).write_text(page, encoding='utf-8', newline='\n')


def validate_inputs():
    for item in json.loads((ROOT / 'inputs' / 'manifest.json').read_text(encoding='utf-8')):
        if sha(ROOT / 'inputs' / item['file']) != item['sha256']:
            raise ValueError('Retained input hash mismatch: ' + item['file'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=ROOT / 'cache')
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    parser.add_argument('--offline', action='store_true')
    parser.add_argument('--build-commit', default=None, help='commit of this script, linked from Appendix A')
    args = parser.parse_args(argv)
    global BUILD_COMMIT
    BUILD_COMMIT = args.build_commit or BUILD_COMMIT
    out, cache = args.output_dir.resolve(), args.data_dir.resolve()
    cache.mkdir(parents=True, exist_ok=True)
    for folder in ['data', 'figures']:
        (out / folder).mkdir(parents=True, exist_ok=True)
    validate_inputs()
    pins = json.loads((ROOT / 'inputs' / 'source-pins.json').read_text(encoding='utf-8'))
    if set(pins) != set(FILES):
        raise ValueError('Every source needs an issued pin')
    records = [cache_source(cache, n, u, args.offline, pins[n]) for n, u in FILES.items()]
    for record in records:
        record['role'] = ('Column check of the permit file' if record['file'] == 'APDRawData.zip' else
                          'Offline chart library' if record['file'].endswith('.js') else
                          'Map land outline' if record['file'] == LAND else
                          'Duration analysis and map' if record['file'] == 'BoreholeRawData.zip' else 'Duration analysis')
        record['file_date'] = archive_date(cache / record['file']) if record['file'].endswith('.zip') else ''
    records.insert(0, dict(file='APDRawData.zip (file of 2 November 2026)', url=URL_BASE+'APDRawData.zip', retrieved_utc='2026-11-03T02:28Z', sha256=OLD_SHA, role='Counts for Figures 2 to 5 and Table 1', file_date='2026-11-02'))
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
    wells, map_audit = map_wells(bore)
    summary = map_summary(wells)
    write_csv(wells, out, 'map-wells')
    write_csv(summary.reset_index(), out, 'map-summary')
    write_csv(map_audit, out, 'map-selection')
    rig, depth, table = [pd.read_csv(ROOT / 'inputs' / n) for n in ['fig-p1-new-well-permits-by-rig-type.csv', 'new-well-permits-by-water-depth.csv', 'table1.csv']]
    if not rig.total.equals(depth.permits) or not rig.year.equals(depth.year):
        raise ValueError('Annual totals differ between the rig-type and water-depth files')
    for frame, name in [(rig, 'fig-p1-new-well-permits-by-rig-type'), (depth, 'new-well-permits-by-water-depth'), (table, 'table1')]:
        write_csv(frame, out, name)
    matplotlib.rcParams.update({'svg.hashsalt': 'issue2-public-data-' + TAG, 'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    payload = [map_figure(wells, land_rings(cache / LAND), out)] + count_figures(rig, depth, out) + days_figures(stats, out)
    build_html(out, cache, payload, stats, sources, audit, dict(summary=summary, audit=map_audit))
    print(stats.to_string(index=False), flush=True)


if __name__ == '__main__':
    main()
