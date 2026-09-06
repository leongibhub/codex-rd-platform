"""Read-only V3 work projection; never invent V2 runs or progress."""
from .store import Store


def project_agents(connection, agents, project_id, now):
    where = '' if project_id is None else ' WHERE project_id=?'
    params = () if project_id is None else (project_id,)
    work = [Store.loads(row['data']) for row in connection.execute(
        'SELECT data FROM lc_work_orders' + where, params)]
    stages = {row['id']: Store.loads(row['data'])['state'] for row in connection.execute(
        'SELECT id,data FROM lc_projects')}
    for agent in agents:
        agent.update(effective_status='WORKING' if agent['status'] == 'BUSY' else 'IDLE', current_work=None)
        # A current V2 run remains authoritative for this agent.
        if agent['status'] == 'BUSY':
            continue
        owned = [w for w in work if w.get('agent_id') == agent['id']]
        if not owned:
            continue
        active = [w for w in owned if w['status'] == 'CLAIMED']
        current = max(active or owned, key=lambda w: w.get('finished_at') or w.get('heartbeat_at') or w['created_at'])
        state = current['status']
        blocked = current.get('summary') if state in {'BLOCKED', 'FAILED', 'WAITING_USER'} else None
        if state == 'CLAIMED':
            if current.get('lease_until', '') <= now:
                state, blocked = 'BLOCKED', 'Work lease expired; process outcome requires reconciliation'
            elif stages.get(current['project_id']) in {'PAUSED', 'CLOSED', 'FAILED'}:
                state, blocked = 'BLOCKED', 'Lifecycle no longer permits execution'
            else:
                state = {'tester': 'TESTING', 'reviewer': 'REVIEWING', 'requirement_analyst': 'ANALYZING',
                         'architect': 'PLANNING'}.get(agent['role'], 'WORKING')
        state = {'WAITING_USER': 'WAITING_FOR_USER', 'READY': 'IDLE'}.get(state, state)
        next_work = [{'id': w['id'], 'role': w['required_role'], 'activity': w['activity'], 'status': w['status']}
                     for w in work if current['id'] in w['dependencies']]
        agent['effective_status'] = state
        agent['current_work'] = {key: current.get(key) for key in (
            'id', 'project_id', 'gate_id', 'activity', 'why', 'input_refs', 'output_refs',
            'heartbeat_at', 'lease_until', 'attempt', 'version')}
        agent['current_work'].update(progress_percent=100 if state == 'DONE' else None,
                                     blocked_reason=blocked, next_handoff=next_work)
    return agents
