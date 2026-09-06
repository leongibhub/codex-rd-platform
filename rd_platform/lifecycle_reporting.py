"""Formal lifecycle report projection; no evidence, approvals or state writes."""
from collections import Counter
from datetime import datetime, timezone


TEST_TYPES = ('FUNCTIONAL', 'NEGATIVE', 'BOUNDARY', 'PERFORMANCE', 'STRESS',
              'STABILITY', 'COMPATIBILITY', 'SECURITY', 'RECOVERY', 'DATA_CONSISTENCY')


def lifecycle_report(snapshot: dict) -> dict:
    """Summarize current case versions separately from historical executions.

    A PASS applies to declared current test scope only. Missing pages, remaining
    Gate decisions or acceptance never become release permission.
    """
    if not isinstance(snapshot, dict):
        raise ValueError('lifecycle snapshot must be an object')
    cases = [c for c in snapshot.get('test_cases', []) if c.get('state') != 'OBSOLETE']
    executions = snapshot.get('test_executions', [])
    rows = []
    for case in cases:
        matching = [e for e in executions if e.get('case_id') == case['id']
                    and e.get('case_version') == case.get('version', 1)]
        latest = matching[-1] if matching else {}
        result = latest.get('result', 'NOT_EXECUTED')
        if case.get('status') == 'REVIEW_REQUIRED':
            result = 'NOT_EXECUTED'
        if result not in {'PASS', 'FAIL', 'BLOCKED', 'NOT_EXECUTED'}:
            result = 'NOT_EXECUTED'
        rows.append({'case_id':case['id'], 'case_version':case.get('version', 1),
                     'requirement_refs':case.get('requirement_refs', []),
                     'test_type':case.get('test_type', 'UNSPECIFIED'), 'result':result,
                     'execution_id':latest.get('id'), 'evidence_refs':latest.get('evidence_refs', [])})
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
        'historical_execution_counts':dict(Counter(e.get('result', 'NOT_EXECUTED') for e in executions)),
        'test_types':types, 'case_results':rows, 'defects':{'total':len(defects), 'open':len(opened),
            'severity':dict(Counter(d.get('severity', 'UNCLASSIFIED') for d in opened)), 'items':opened},
        'traceability':snapshot.get('traceability', []), 'gates':snapshot.get('gates', []),
        'conclusion':conclusion, 'recommend_release':not reasons, 'release_reasons':reasons,
        'execution_records':executions,
        'note':'CONDITIONAL PASS is not permission to release; unexecuted types are not coverage claims.'}
