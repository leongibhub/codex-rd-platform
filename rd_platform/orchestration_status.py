"""Read-only explanations of stage admission, not permission to run tools."""
from .lifecycle import LifecycleService
from .orchestration_policy import strict_project, validate_claim


def orchestration_status(runtime, project_id, *, limit=200):
    service = LifecycleService()
    service.integer(limit, 'limit', 1, 500)
    with runtime.store.transaction(write=False) as connection:
        project = service.project(connection, project_id)
        gates = service.project_gates(connection, project_id)['gates']
        work = service.rows(connection, 'work_orders', project_id)
        by_id = {w['id']: w for w in work}
        rows = []
        for item in work[:limit]:
            admission, reason = 'NOT_READY', 'Work status: ' + item['status']
            if project['state'] in {'PAUSED', 'CLOSED', 'FAILED', 'WAITING_USER'}:
                reason = 'Lifecycle state: ' + project['state']
            elif item['status'] == 'READY':
                try:
                    validate_claim(service, connection, item)
                    for dependency in item['dependencies']:
                        if by_id[dependency]['status'] != 'DONE':
                            raise ValueError('DEPENDENCY_NOT_DONE:' + dependency)
                    service.refs(connection, project_id, item['input_refs'], nonempty=False)
                    admission, reason = 'ALLOWED', 'Stage prerequisites are current; worker identity, lease and retry safety still require admission.'
                except (KeyError, ValueError) as exc:
                    admission, reason = 'WAITING_PREREQUISITE', str(exc)
            rows.append({key: item.get(key) for key in ('id', 'gate_id', 'activity', 'why', 'required_role',
                         'status', 'attempt', 'version', 'dependencies', 'input_refs', 'output_refs')})
            rows[-1].update(stage_admission=admission, reason=reason)
        earliest = next((g['gate_id'] for g in gates if g['gate_status'] != 'PASS'), 'G11')
        return service.redact_projection({
            'schema_version': 'orchestration-status-v1', 'project_id': project_id,
            'project_state': project['state'], 'current_gate': earliest,
            'strict_policy': strict_project(service, connection, project_id),
            'gates': [{'gate_id': g['gate_id'], 'gate_status': g['gate_status'], 'freshness': g['freshness']} for g in gates],
            'total_work_orders': len(work), 'truncated': len(work) > limit, 'work_orders': rows,
            'execution_authorized': False,
            'note': 'Read-only stage admission; not an executed work claim, Gate decision, human approval or release. Use lifecycle-collection for remaining work pages.',
        })
