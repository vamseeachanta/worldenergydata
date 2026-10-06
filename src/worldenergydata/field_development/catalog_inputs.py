"""Pinned input decoding and unambiguous identity helpers for catalog integration."""
import csv
import hashlib
import io
import json
import re
from pathlib import Path

TABLES = ('sources', 'field_observations', 'cost_observations',
          'milestone_observations', 'inherited_cost_records')
AUTHORITY_NOTE = 'Signoff metadata records an evidence claim, not authenticated action or publication authority.'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def strict_json(raw):
    def unique_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, 'duplicate JSON key')
            result[key] = value
        return result
    return json.loads(raw.decode('utf-8'), object_pairs_hook=unique_pairs)


def csv_input(raw):
    reader = csv.DictReader(io.StringIO(raw.decode('utf-8-sig'), newline=''), strict=True)
    header, rows = reader.fieldnames, list(reader)
    require(header and len(header) == len(set(header)) and
            not any(None in row or None in row.values() for row in rows),
            'invalid CSV header/row width')
    return header, rows


def pinned_inputs(snapshot, legacy_csv, parent_csv, validate):
    snapshot = Path(snapshot)
    manifest_raw = (snapshot / 'manifest.json').read_bytes()
    manifest = strict_json(manifest_raw)
    require(isinstance(manifest, dict), 'invalid snapshot manifest type')
    require(isinstance(manifest.get('dataset_id'), str) and
            re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', manifest['dataset_id']), 'invalid dataset identity')
    entries = manifest.get('files')
    require(isinstance(entries, list) and all(isinstance(p, dict) for p in entries), 'invalid snapshot pins')
    names = [p.get('path') for p in entries]
    require(all(isinstance(n, str) for n in names) and len(set(names)) == len(names), 'duplicate or invalid snapshot pin')
    require(all(Path(n).name == n for n in names), 'unsafe snapshot pin')
    pins = {p['path']: p for p in entries}
    tables, hashes = {}, {}
    for table in TABLES:
        name = table + '.json'; pin = pins.get(name, {})
        require(type(pin.get('record_count')) is int and pin['record_count'] >= 0, 'invalid snapshot count')
        require(isinstance(pin.get('sha256'), str) and re.fullmatch('[a-f0-9]{64}', pin['sha256']), 'invalid input digest')
        raw = (snapshot / name).read_bytes(); digest = hashlib.sha256(raw).hexdigest()
        require(digest == pin['sha256'], 'input digest mismatch: ' + name)
        tables[table] = strict_json(raw)
        require(isinstance(tables[table], list) and all(isinstance(r, dict) for r in tables[table]), 'invalid table type')
        require(len(tables[table]) == pin['record_count'], 'input count mismatch: ' + name)
        hashes[name] = digest
    legacy_raw, parent_raw = Path(legacy_csv).read_bytes(), Path(parent_csv).read_bytes()
    hashes.update(legacy_catalog=hashlib.sha256(legacy_raw).hexdigest(), inherited_cost_parent=hashlib.sha256(parent_raw).hexdigest(), original_manifest=hashlib.sha256(manifest_raw).hexdigest())
    require(hashes['inherited_cost_parent'] == manifest.get('inherited_cost_input', {}).get('sha256'), 'parent cost input digest mismatch')
    validate(tables)
    return manifest, tables, hashes, (csv_input(legacy_raw), csv_input(parent_raw))


def name_candidate(entities, scope, name):
    matches = [e for e in entities if e['entity_type'] == scope and e['primary_name'] == name]
    require(len(matches) <= 1, 'ambiguous entity type/name candidate')
    return matches[0] if matches else None


def scope_claims(evidence):
    for row in evidence['field_observations']:
        if row.get('development') not in {None, '', 'Unassigned'}:
            yield 'development', row['development'], 'field_observations', row
    for row in evidence['cost_observations']:
        scope = {'project': 'development', 'block': 'block', 'contract_bundle': 'contract_bundle'}.get(row['scope_type'])
        if scope:
            yield scope, row['entity_or_scope'], 'cost_observations', row
    for row in evidence['milestone_observations']:
        scope = next((s for s in ('well', 'phase') if row['scope'].startswith(s)), None)
        if scope:
            yield scope, row['subject'], 'milestone_observations', row


def parent_link(row, cached_parent, fingerprint):
    header, parents = cached_parent
    require({'PROJECT', 'SOURCE_URL'} <= set(header), 'invalid parent CSV columns')
    matches = [p for p in parents if p['PROJECT'] == row.get('project') and p['SOURCE_URL'] == row.get('source_url')]
    require(len(matches) == 1, 'inherited cost requires one exact parent project/source URL')
    digest = fingerprint([matches[0][column] for column in header])
    pid = 'sanctioned_projects:row:' + digest
    return dict(record_id=pid, sha256=digest, table='parent_reference')
