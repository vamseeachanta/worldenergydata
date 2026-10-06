"""Negative contracts for identity/source/parent linkage (issue 1144)."""
import copy
import hashlib
import json
from pathlib import Path
import pytest
from test_catalog_integration import api, inputs, write_json


def replace_table(inputs, table, rows):
    snapshot=inputs[0]; path=snapshot/(table+'.json'); write_json(path,rows)
    manifest=json.loads((snapshot/'manifest.json').read_text())
    pin=next(p for p in manifest['files'] if p['path']==table+'.json')
    pin.update(record_count=len(rows),sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    write_json(snapshot/'manifest.json',manifest)


def test_field_self_link_uses_original_id_with_duplicate_names(api, inputs):
    bundle=api.build_integration(*inputs)
    rows=bundle['evidence']['field_observations']
    rows[1]['name']=rows[0]['name']
    entities=api.build_registry(bundle['manifest']['dataset_id'],rows)
    evidence=dict(bundle['evidence'],cost_observations=[],milestone_observations=[])
    links=api.build_links(bundle['manifest']['dataset_id'],evidence,entities,inputs[2])
    for row in rows:
        link=next(r for r in links['records'] if r['record_id']==api.record_id(bundle['manifest']['dataset_id'],'field_observations',row))
        assert link['entity_id']==bundle['manifest']['dataset_id']+':'+row['entity_id']


def test_ambiguous_name_candidate_raises(api, inputs):
    bundle=api.build_integration(*inputs); entities=bundle['entities']
    original=next(e for e in entities if e['entity_type']=='development' and e['primary_name']=='Dalia')
    entities.append(dict(original,entity_id='other-development'))
    with pytest.raises(ValueError,match='ambiguous'):
        api.build_links(bundle['manifest']['dataset_id'],bundle['evidence'],entities,inputs[2])


def test_name_only_scope_links_are_candidates(api, inputs):
    bundle=api.build_integration(*inputs)
    assert all(r['link_status']=='candidate' for r in bundle['links']['records'] if r['table']=='cost_observations')


def test_same_name_phases_under_different_parents_not_merged(api, inputs):
    rows=[dict(subject='Phase 1',scope='phase',development=parent,source_ref='s1',event_date='2026',precision='year') for parent in ('A','B')]
    replace_table(inputs,'milestone_observations',rows)
    with pytest.raises(ValueError,match='parent|scope'):
        api.build_integration(*inputs)


@pytest.mark.parametrize('table',['field_observations','cost_observations','milestone_observations'])
@pytest.mark.parametrize('value',[None,''])
def test_non_source_evidence_requires_source(api, inputs,table,value):
    rows=json.loads((inputs[0]/(table+'.json')).read_text()); rows[0]['source_ref']=value
    replace_table(inputs,table,rows)
    with pytest.raises(ValueError,match='source'):
        api.build_integration(*inputs)


@pytest.mark.parametrize('rows',['PROJECT,SOURCE_URL\nOther,https://example.org/dalia\n','PROJECT,SOURCE_URL\nDalia,https://example.org/dalia\nDalia,https://example.org/dalia\n'])
def test_inherited_requires_one_exact_parent(api,inputs,rows):
    inputs[2].write_text(rows,encoding='utf-8')
    manifest=json.loads((inputs[0]/'manifest.json').read_text()); manifest['inherited_cost_input']['sha256']=hashlib.sha256(inputs[2].read_bytes()).hexdigest(); write_json(inputs[0]/'manifest.json',manifest)
    with pytest.raises(ValueError,match='parent'):
        api.build_integration(*inputs)


def test_reader_rejects_inherited_link_without_parent(api,inputs):
    bundle=api.build_integration(*inputs)
    link=next(r for r in bundle['links']['records'] if r['table']=='inherited_cost_records')
    link['dependencies']=[]; link.pop('parent_record_id'); link['link_status']='unresolved'
    with pytest.raises(ValueError,match='parent'):
        api.validation.validate_links(bundle,{e['entity_id'] for e in bundle['entities']},{'s1'})


def test_duplicate_snapshot_pin_rejected(api,inputs):
    manifest=json.loads((inputs[0]/'manifest.json').read_text()); manifest['files'].append(manifest['files'][0]); write_json(inputs[0]/'manifest.json',manifest)
    with pytest.raises(ValueError,match='duplicate'):
        api.build_integration(*inputs)

def test_each_legacy_parent_manifest_read_is_single_pinned_buffer(api,inputs,monkeypatch):
    reads={}; original=Path.read_bytes
    def observed(path):
        reads[path]=reads.get(path,0)+1
        return original(path)
    monkeypatch.setattr(Path,'read_bytes',observed)
    bundle=api.build_integration(*inputs)
    for path in (inputs[1],inputs[2],inputs[0]/'manifest.json'):
        assert reads[path]==1
        assert hashlib.sha256(original(path)).hexdigest() in bundle['manifest']['input_hashes'].values()


def test_raw_phase_relationship_type(api,inputs):
    rows=json.loads((inputs[0]/'field_observations.json').read_text())
    rows[3].update(entity_type='phase',development='Phase parent')
    replace_table(inputs,'field_observations',rows)
    bundle=api.build_integration(*inputs)
    assert next(r for r in bundle['relationships'] if r['subject_entity_id'].endswith(':ao-phase'))['predicate']=='phase_of'

@pytest.mark.parametrize('table,key,value', [('field_observations','name',''),('field_observations','country',None),('cost_observations','scope_type','field'),('milestone_observations','event_date','2029-99-99')])
def test_invalid_required_input_semantics(api,inputs,table,key,value):
    rows=json.loads((inputs[0]/(table+'.json')).read_text()); rows[0][key]=value
    replace_table(inputs,table,rows)
    with pytest.raises(ValueError):
        api.build_integration(*inputs)

@pytest.mark.parametrize('key,value',[('sha256','0'*64),('table','sources')])
def test_eligibility_cannot_overwrite_computed_identity(api,inputs,key,value):
    bundle=api.build_integration(*inputs); row=dict(bundle['eligibility'][0]); row[key]=value
    with pytest.raises(ValueError,match='computed'):
        api.eligibility_matrix(bundle['links'],[row])


def test_default_eligibility_does_not_supply_reviewer_basis(api,inputs):
    bundle=api.build_integration(*inputs)
    assert all(r['basis'] is None and r['proposed_decision']=='unresolved' for r in bundle['eligibility'])
    row=dict(bundle['eligibility'][0],decision='eligible_factual_derivative',reviewer='Vamsee',approval_ref='evidence',reviewed_sha256=bundle['eligibility'][0]['sha256'])
    with pytest.raises(ValueError,match='signoff'):
        api.eligibility_matrix(bundle['links'],[row])

def test_reader_requires_matching_parent_fingerprint(api,inputs):
    bundle=api.build_integration(*inputs)
    next(r for r in bundle['links']['records'] if r['table']=='inherited_cost_records')['parent_row_fingerprint']='0'*64
    with pytest.raises(ValueError,match='parent'):
        api.validation.validate_links(bundle,{e['entity_id'] for e in bundle['entities']},{'s1'})
