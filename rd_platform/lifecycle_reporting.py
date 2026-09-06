"""Formal lifecycle report projection; no evidence, approvals or state writes."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import re
from urllib.parse import urlsplit, urlunsplit

from .store import Store


TEST_TYPES = ('FUNCTIONAL', 'NEGATIVE', 'BOUNDARY', 'PERFORMANCE', 'STRESS',
              'STABILITY', 'COMPATIBILITY', 'SECURITY', 'RECOVERY', 'DATA_CONSISTENCY')


def sanitize_report_value(value):
    """Metadata-only export: redact secrets and omit raw content and commands."""
    from .lifecycle_base import LifecycleBase
    if isinstance(value,dict):
        omitted={'inline_json','stdout','stderr','argv','repository_root','environment_variables'}
        return {key:sanitize_report_value(item) for key,item in value.items() if key not in omitted and not re.search(r'(?i)(?:token|password|authorization|cookie|private_key|secret|api[_-]?key|lease_digest|release_digest)',key)}
    if isinstance(value,list): return [sanitize_report_value(item) for item in value]
    if not isinstance(value,str): return value
    value=LifecycleBase.redact_text(value)
    def clean_url(match):
        try:
            parsed=urlsplit(match.group(0)); host=parsed.hostname or ''
            if parsed.port: host+=':'+str(parsed.port)
            return urlunsplit((parsed.scheme,host,parsed.path,'',''))
        except ValueError: return '[REDACTED_URL]'
    return re.sub(r'https?://[^\s<>\"\']+',clean_url,value)


def lifecycle_report(snapshot: dict) -> dict:
    """Summarize current case versions separately from historical executions.

    A PASS applies to declared current test scope only. Missing pages, remaining
    Gate decisions or acceptance never become release permission.
    """
    if not isinstance(snapshot, dict):
        raise ValueError('lifecycle snapshot must be an object')
    cases = [c for c in snapshot.get('test_cases', []) if c.get('state') != 'OBSOLETE']
    executions = snapshot.get('test_executions', [])
    latest_by_case = {(e.get('case_id'),e.get('case_version')):e for e in executions}
    rows = []
    for case in cases:
        latest = latest_by_case.get((case['id'],case.get('version',1)),{})
        result = latest.get('result', 'NOT_EXECUTED')
        if case.get('status') == 'REVIEW_REQUIRED':
            result = 'NOT_EXECUTED'
        if result not in {'PASS', 'FAIL', 'BLOCKED', 'NOT_EXECUTED'}:
            result = 'NOT_EXECUTED'
        rows.append({'case_id':case['id'], 'case_version':case.get('version', 1),
                     'requirement_refs':case.get('requirement_refs', []),
                     'test_type':case.get('test_type', 'UNSPECIFIED'), 'result':result,
                     'execution_id':latest.get('id'), 'evidence_refs':latest.get('evidence_refs', []),
                     'observed_result':latest.get('observed_result',latest.get('result','NOT_EXECUTED')),
                     'freshness':latest.get('freshness','NOT_CHECKED'),
                     'freshness_reason':latest.get('freshness_reason')})
    counts = {s:sum(r['result'] == s for r in rows) for s in ('PASS', 'FAIL', 'BLOCKED', 'NOT_EXECUTED')}
    executed = counts['PASS'] + counts['FAIL']
    complete = not any(snapshot.get('collections_truncated', {}).values())
    defects = snapshot.get('defects', [])
    opened = [d for d in defects if d.get('status') != 'CLOSED']
    critical = [d for d in opened if d.get('severity') in {'BLOCKER', 'CRITICAL', 'UNCLASSIFIED'}]
    if counts['FAIL'] or critical:
        conclusion = 'FAIL'
    elif not rows or counts['BLOCKED'] or counts['NOT_EXECUTED'] or not complete:
        conclusion = 'CONDITIONAL PASS'
    else:
        conclusion = 'PASS'
    types = {}
    for typ in TEST_TYPES:
        selected = [r for r in rows if r['test_type'] == typ]
        statuses = {r['result'] for r in selected}
        types[typ] = {'cases':len(selected), 'status':('FAIL' if 'FAIL' in statuses else
            'PASS' if statuses == {'PASS'} else 'NOT_EXECUTED' if not selected else 'INCOMPLETE')}
    gates = {g['gate_id']:g.get('gate_status') for g in snapshot.get('gates', [])}
    trace_gaps = [r for r in snapshot.get('traceability', []) if r.get('status') != 'COMPLETE']
    reasons = []
    if conclusion != 'PASS': reasons.append('current declared test scope is not fully passing')
    if not complete: reasons.append('snapshot collections are truncated; report counts are partial')
    if opened: reasons.append('unclosed defects require disposition')
    if trace_gaps or not snapshot.get('traceability'): reasons.append('requirement traceability is incomplete')
    releases = snapshot.get('releases', [])
    if not releases or any(r.get('status') not in {'READY', 'RELEASED'} for r in releases):
        reasons.append('release is absent, changed, failed, rolled back or not ready')
    if any(gates.get('G'+str(n)) != 'PASS' for n in range(11)):
        reasons.append('G0–G10 release and human acceptance decisions are not all PASS')
    return {'report_scope':'LIFECYCLE_DECLARED_TEST_SCOPE', 'project_id':snapshot.get('project_id'),
        'generated_at':datetime.now(timezone.utc).isoformat(), 'software_versions':snapshot.get('releases', []),
        'test_environment':[e for e in snapshot.get('evidence', []) if e.get('kind') == 'test_environment'],
        'test_strategy':snapshot.get('test_models', []), 'total':len(rows), 'executed':executed,
        'counts':counts, 'pass_rate':counts['PASS']/executed if executed else None,
        'complete_snapshot':complete, 'collection_counts':snapshot.get('collection_counts', {}),
        'historical_execution_counts':dict(Counter(e.get('observed_result',e.get('result', 'NOT_EXECUTED')) for e in executions)),
        'test_types':types, 'case_results':rows, 'defects':{'total':len(defects), 'open':len(opened),
            'severity':dict(Counter(d.get('severity', 'UNCLASSIFIED') for d in opened)), 'items':opened},
        'traceability':snapshot.get('traceability', []), 'gates':snapshot.get('gates', []),
        'conclusion':conclusion, 'recommend_release':not reasons, 'release_reasons':reasons,
        'execution_records':executions,
        'source_revision':snapshot.get('source_revision'),
        'note':'CONDITIONAL PASS is not permission to release; unexecuted types are not coverage claims.'}


def _project_execution_evidence(service, connection, project_id, execution):
    """Reapply admission evidence checks without altering historical records."""
    observed=execution.get('result')
    projection=dict(execution,observed_result=observed,freshness='NOT_APPLICABLE',freshness_reason=None)
    if observed not in {'PASS','FAIL'}: return projection
    try:
        if execution.get('status')!='FINISHED': raise ValueError('execution is not finished')
        case_ref={'type':'TEST_CASE','id':execution['case_id'],'version':execution['case_version']}
        service.ref(connection,project_id,case_ref)
        case=service.get(connection,'test_cases',execution['case_id'])
        if case.get('state') not in {'BASELINED','APPROVED'} or case.get('status')=='REVIEW_REQUIRED':
            raise ValueError('executed case is not current baselined scope')
        service.agent(connection,execution.get('executor_id'),{'tester'})
        service.refs(connection,project_id,execution.get('requirement_refs'))
        service.evidence_refs(connection,project_id,[execution.get('environment_ref')],kinds={'test_environment'})
        evidence=service.evidence_refs(connection,project_id,execution.get('evidence_refs'),kinds={'test_execution'},roles={'tester'})
        for item in evidence:
            metadata=item.get('metadata',{})
            if item.get('recorded_by')!=execution['executor_id'] or metadata.get('execution_id')!=execution['id'] or metadata.get('result')!=observed:
                raise ValueError('execution evidence identity or result mismatch')
            if case_ref not in metadata.get('artifact_refs',[]): raise ValueError('evidence does not lock executed case version')
            if item.get('observed_at','')<execution['created_at']: raise ValueError('execution evidence predates execution')
        projection['freshness']='CURRENT'
    except (ValueError,KeyError,TypeError,OSError) as error:
        projection.update(result='BLOCKED',freshness='STALE',freshness_reason='CURRENT_EVIDENCE_UNVERIFIABLE: '+str(error))
    return projection


def _capture_project(runtime, project_id, *, page_size=200, include_versions=False):
    """Collect complete public pages from one SQLite read transaction.

    Revision hashes cover raw source records, including immutable versions and
    events, without copying their contents into the exported revision metadata.
    """
    from .lifecycle import LifecycleService
    from .lifecycle_query import LifecycleCollectionQuery, COLLECTIONS
    service=LifecycleService(); service.integer(page_size,'page_size',1,500)
    query=LifecycleCollectionQuery()
    version_index={'artifacts':[],'test_cases':[],'releases':[]}
    with runtime.store.transaction(write=False) as connection:
        project=service.project(connection,project_id)
        snapshot={'project_id':project_id,'schema_version':'lifecycle-v1','lifecycle':project,
                  'collection_counts':{},'collections_truncated':{}}
        fingerprint=hashlib.sha256()
        for collection in sorted(COLLECTIONS):
            items=[]; cursor=None; seen_cursors=set()
            while True:
                page=query.read(connection,project_id,collection,limit=page_size,after_cursor=cursor)
                items.extend(page['items'])
                if not page['has_more']: break
                cursor=page['next_cursor']
                if not cursor or cursor in seen_cursors: raise ValueError('collection pagination did not advance')
                seen_cursors.add(cursor)
            if len(items)!=page['total'] or len({item['id'] for item in items})!=len(items): raise ValueError('incomplete or duplicate collection page')
            if collection=='gate_assessments':
                status={row['id']:row['status'] for row in connection.execute('SELECT id,status FROM lc_gate_assessments WHERE project_id=?',(project_id,))}
                for item in items:
                    if status[item['id']]=='SUPERSEDED': item['status']='SUPERSEDED'
            snapshot[collection]=items; snapshot['collection_counts'][collection]=len(items)
            snapshot['collections_truncated'][collection]=False
            fingerprint.update(collection.encode())
            for row in connection.execute(f'SELECT id,status,data FROM lc_{collection} WHERE project_id=? ORDER BY rowid',(project_id,)):
                fingerprint.update(Store.dumps(tuple(row)).encode())
        fingerprint.update(Store.dumps(project).encode())
        snapshot['test_executions']=[_project_execution_evidence(service,connection,project_id,item) for item in snapshot['test_executions']]
        snapshot['traceability']=service.trace_summary(connection,project_id)
        stale=next((g['gate_id'] for g in snapshot['gates'] if g.get('freshness')=='STALE'),None)
        if stale:
            snapshot['lifecycle']=dict(project,current_gate=stale,state='PAUSED' if project['state']=='PAUSED' else 'BLOCKED')
        for label,table,key,parent in [('artifacts','lc_artifact_versions','artifact_id','lc_artifacts'),('test_cases','lc_test_case_versions','case_id','lc_test_cases'),('releases','lc_release_versions','release_id','lc_releases')]:
            fingerprint.update(table.encode())
            for row in connection.execute(f'SELECT v.{key},v.version,v.data FROM {table} v JOIN {parent} p ON p.id=v.{key} WHERE p.project_id=? ORDER BY v.{key},v.version',(project_id,)):
                fingerprint.update(Store.dumps(tuple(row)).encode())
                if include_versions:
                    data=Store.loads(row['data'])
                    version_index[label].append({'id':row[key],'version':row['version'],'state':data.get('state',data.get('status')),
                        'artifact_type':data.get('artifact_type'),'content_sha256':data.get('content_ref',{}).get('sha256'),
                        'record_sha256':hashlib.sha256(row['data'].encode()).hexdigest(),'created_at':data.get('created_at'),
                        'created_by':data.get('created_by'),'source':data.get('source')})
        fingerprint.update(b'lc_events')
        event_count=0; last_event_sequence=0
        for row in connection.execute('SELECT * FROM lc_events WHERE project_id=? ORDER BY sequence',(project_id,)):
            fingerprint.update(Store.dumps(tuple(row)).encode()); event_count+=1; last_event_sequence=row['sequence']
        migrations=[dict(row) for row in connection.execute('SELECT * FROM lc_migrations ORDER BY version')]
        fingerprint.update(Store.dumps(migrations).encode())
        snapshot['source_revision']={'scheme':'lifecycle-project-records-v1','sha256':fingerprint.hexdigest(),
                                     'project_id':project_id,'event_count':event_count,'last_event_sequence':last_event_sequence,
                                     'migrations':[{'version':m['version'],'sha256':m['sha256']} for m in migrations]}
    return sanitize_report_value(snapshot),sanitize_report_value(version_index)


def lifecycle_report_from_runtime(runtime, project_id, *, page_size=200):
    """Complete, consistent current-scope report; never the first 500 rows only."""
    snapshot,_=_capture_project(runtime,project_id,page_size=page_size)
    return lifecycle_report(snapshot)
