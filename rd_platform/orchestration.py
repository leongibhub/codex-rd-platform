"""Bootstrap a resumable lifecycle from one idea, without inventing decisions."""
import hashlib
from pathlib import Path

from .orchestration_policy import STRICT_POLICY


STAGES = (
    ('G0', 'requirement_analyst', 'Initial requirement model', 'DOC',
     'Analyze the idea before asking questions: goals, users, workflows, data, permissions, risks, omissions and acceptance. Separate supplied facts, assumptions and unknowns; ask only material questions.'),
    ('G1', 'researcher', 'Feasibility and evidence research', 'DOC',
     'Assess technical feasibility and relevant alternatives using traceable sources. State unavailable evidence; do not invent citations.'),
    ('G2', 'product_manager', 'Product definition', 'PRD',
     'Define users, scenarios, prioritized scope, out of scope, measurable goals and product acceptance.'),
    ('G3', 'requirement_analyst', 'Requirements and acceptance model', 'REQ',
     'Derive testable functional and nonfunctional requirements, exceptions, interfaces, data and acceptance; preserve unresolved material decisions.'),
    ('G4', 'architect', 'Architecture and detailed design', 'DES',
     'Design components, interfaces, persistence, deployment, security and failure handling with tradeoffs and requirement references.'),
    ('G5', 'architect', 'Task and test planning', 'TASK',
     'Break requirements into bounded dependency-linked modules. Define a risk-based test model before cases and independent developer/tester/reviewer assignments.'),
    ('G6', 'developer', 'Implement and unit verify modules', 'CODE_CHANGE',
     'Implement scoped modules with unit tests, integration seams and actual local verification. Do not replace independent tests or reviews with your own conclusion.'),
    ('G7', 'tester', 'Independent system and automated testing', 'DOC',
     'Read requirements as an end user; create test model, precise cases, executable automation, actual results and defects. Execute applicable checks; do not equate scripts with tests run.'),
    ('G8', 'reviewer', 'Independent code and evidence review', 'DOC',
     'Independently inspect code and test evidence for correctness, security and gaps. Record actionable findings; return failed implementation to its owner before recommending completion.'),
    ('G9', 'documentation_manager', 'Acceptance package', 'DOC',
     'Assemble requirement coverage and known issues for the actual human. Never sign or approve on their behalf. Return WAITING_USER if an applicable signed acceptance is absent.'),
    ('G10', 'release_manager', 'Release and deployment', 'DOC',
     'Prepare installation, deployment, rollback and operations material. Execute only authorized targets through the deployment adapter after actual release gates; otherwise WAITING_USER with the missing authority.'),
    ('G11', 'documentation_manager', 'Closure and lessons', 'DOC',
     'Reconcile delivered scope, real acceptance and release evidence, remaining issues and reusable lessons. Do not declare closed while required evidence is absent.'),
)


def start_project(runtime, *, name, idea, repository_root, request_id):
    """Idempotent host bootstrap. Work completion never implies Gate PASS."""
    if not all(isinstance(v, str) and v.strip() for v in (name, idea, request_id)):
        raise ValueError('name, idea and request_id are required')
    if len(idea) > 32000 or len(name) > 200 or len(request_id) > 200:
        raise ValueError('bootstrap input exceeds budget')
    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError('repository_root must be a directory')
    # Include root in the idempotent payload before any lifecycle mutation.
    p = runtime.execute('project.create', {'name': name, 'idea': idea, 'bootstrap_root': str(root)},
                        request_id='bootstrap:' + request_id)
    pid = p['id']
    actor = 'orchestrator:' + pid
    runtime.execute('agent.register', {'id': actor, 'role': 'requirement_analyst'},
                    request_id=pid + ':actor')
    runtime.execute('lifecycle.initialize', {'project_id': pid, 'repository_root': str(root), 'mode': 'active'},
                    request_id=pid + ':initialize')
    bg = 'BG-' + hashlib.sha256(pid.encode()).hexdigest()[:16]
    a = runtime.execute('artifact.create', {'project_id': pid, 'artifact_type': 'BG',
        'artifact_id': bg, 'title': name, 'state': 'DRAFT', 'content_ref': {'inline_json': {
            'idea': idea, 'source': 'explicit_user_input', 'approval': 'NOT_AVAILABLE',
            'orchestration_policy': STRICT_POLICY}},
        'source': {'kind': 'host', 'actor': actor}}, request_id=pid + ':idea')
    initial = {'type': 'BG', 'id': a['id'], 'version': a['version']}
    work = []
    for gate, role, activity, output_type, instructions in STAGES:
        w = runtime.execute('work.create', {'project_id': pid, 'gate_id': gate,
            'activity': activity, 'required_role': role, 'why': instructions,
            'input_refs': [initial], 'dependencies': [work[-1]['id']] if work else [],
            'output_contract': {'required_types': [output_type], 'min_outputs': 1},
            'strict_policy': STRICT_POLICY},
            request_id=pid + ':stage:' + gate)
        work.append(w)
    return {'project_id': pid, 'repository_root': str(root), 'work_orders': work,
            'status': 'PLANNED', 'gate_decisions': [],
            'next_action': 'Configure actual workers and run worker-service. PLANNED is not executed or approved.'}
