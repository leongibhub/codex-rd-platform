"""Execute versioned argv cases through the trusted local host, never HTTP.

An exit status verifies only the assertion program chosen by the test author.
This adapter is not a sandbox, test designer, or human approval provider.
"""
from __future__ import annotations

import hashlib
import json
import math
import platform
import sys
from contextlib import ExitStack
from pathlib import Path
from uuid import uuid4

from .lifecycle import LifecycleService
from .runner import run_command
from ._workspace_directory import confined_directory


def run_case(runtime, *, project_id, case_id, case_version, executor_id, timeout=60):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 3600:
        raise ValueError('timeout must be finite and in (0, 3600] seconds')
    svc = LifecycleService()
    # Validate and start against one source version. No DB lock during subprocess.
    with runtime.store.transaction() as c:
        project = svc.project(c, project_id)
        if project['state'] != 'ACTIVE': raise ValueError('lifecycle must be ACTIVE')
        root = Path(project['repository_root']).resolve()
        svc.agent(c, executor_id, {'tester'})
        case = svc.get(c, 'test_cases', case_id)
        if case['project_id'] != project_id or type(case_version) is not int or case['version'] != case_version:
            raise ValueError('case project/version mismatch')
        if case['state'] not in {'BASELINED','APPROVED'}: raise ValueError('case must be baselined')
        automation = case['automation']
        if automation.get('status') != 'AUTOMATED' or automation.get('method') != 'argv':
            raise ValueError('case must bind AUTOMATED argv method')
        # NFR evidence needs its own measured result schema, not process counts.
        if case['test_type'] in {'PERFORMANCE', 'STRESS', 'STABILITY'}:
            raise ValueError('measured NFR cases require a specialized metrics adapter')
        argv = automation.get('argv')
        if not isinstance(argv, list) or not argv or any(not isinstance(a, str) or not a or '\0' in a for a in argv):
            raise ValueError('automation.argv must be a nonempty string array')
        svc.safe_json(argv)
        rendered = []
        for arg in argv:
            for key, value in (('{python}', sys.executable), ('{root}', str(root))):
                arg = arg.replace(key, value)
            if '{' in arg or '}' in arg: raise ValueError('unknown argv placeholder')
            rendered.append(arg)
        cwd_ref = Path(automation.get('cwd', '.'))
        if cwd_ref.is_absolute() or '..' in cwd_ref.parts: raise ValueError('cwd must be repository relative')
        cwd = (root / cwd_ref).resolve()
        if not cwd.is_relative_to(root) or not cwd.is_dir(): raise ValueError('cwd outside repository or missing')
        subjects = svc.refs(c, project_id, automation.get('subject_refs'))
        if any(s['type'] != 'CODE_CHANGE' for s in subjects): raise ValueError('subject_refs must bind CODE_CHANGE artifacts')
        for subject in subjects:
            artifact = svc.get(c, 'artifacts', subject['id'])
            if artifact['state'] not in {'BASELINED', 'APPROVED'} or 'path' not in artifact['content_ref']:
                raise ValueError('executable source subjects need baselined repository file hashes')
        case_ref = {'type':'TEST_CASE', 'id':case_id, 'version':case_version}
        model_ref = {'type':'TEST_MODEL','id':case['test_model_id'],'version':case['test_model_version']}
        locked = [case_ref, model_ref, *case['requirement_refs'], *subjects]
        env = svc.execute(c, 'evidence.register', dict(project_id=project_id, kind='test_environment',
            status='VERIFIED', source={'kind':'host','actor':executor_id}, observed_at=svc.now(),
            locator={'inline_json':{'os':platform.platform(),'python':platform.python_version(),
                                   'executable':sys.executable,'cwd':str(cwd)}}, metadata={}))
        execution = svc.execute(c, 'test_execution.start', dict(case_id=case_id, case_version=case_version,
            executor_id=executor_id, environment_ref={'type':'EVIDENCE','id':env['id'],'version':1}))
    relative = Path('.rd-platform') / 'test-runs' / ('case-' + uuid4().hex) / 'result.json'
    output = root / relative
    with ExitStack() as guards:
        output_guard = None
        try:
            cwd_guard = guards.enter_context(confined_directory(root, cwd_ref))
            try:
                command = run_command(rendered, cwd_guard.path, timeout=timeout, cwd_guard=cwd_guard)
            except Exception as error:
                command = {'status':'FAIL', 'exit_code':None, 'stdout':'', 'duration_seconds':0,
                           'launch_error':type(error).__name__ + ': adapter failed'}
            command = svc.redact_projection(command)
            status = command.get('status')
            if status not in {'PASS','FAIL'}: raise ValueError('runner returned invalid status')
            # Create unpredictable output directories only after the process tree exits.
            output_guard = guards.enter_context(confined_directory(root, relative.parent, create=True))
            payload = {'schema_version':1,'project_id':project_id,'execution_id':execution['id'],
                       'scope':'RAW_COMMAND_OBSERVATION','note':'Runtime execution and admission.json determine admissibility; command exit is not test acceptance.',
                       'case_ref':case_ref,'subject_refs':subjects,'command':command,'recorded_at':svc.now()}
            output_guard.write_new_json('result.json', payload)
            raw = (json.dumps(payload, ensure_ascii=False, allow_nan=False, sort_keys=True, indent=2)+'\n').encode('utf-8')
            with runtime.store.transaction() as c:
                if svc.project(c, project_id)['state'] != 'ACTIVE': raise ValueError('project changed during execution')
                refs = svc.refs(c, project_id, locked)
                evidence = svc.execute(c, 'evidence.register', dict(project_id=project_id,kind='test_execution',
                    status='VERIFIED', source={'kind':'host','actor':executor_id}, observed_at=svc.now(),
                    locator={'path':relative.as_posix(),'sha256':hashlib.sha256(raw).hexdigest()},
                    metadata={'execution_id':execution['id'],'result':status,'artifact_refs':refs}))
                finished = svc.execute(c, 'test_execution.finish', dict(execution_id=execution['id'], result=status,
                    actual_result='Trusted host executed the version-bound assertion command; see hashed result file.',
                    evidence_refs=[{'type':'EVIDENCE','id':evidence['id'],'version':1}]))
        except BaseException as error:
            finished = runtime.execute('test_execution.abort', dict(execution_id=execution['id'],
                executor_id=executor_id, reason=type(error).__name__ + ': command evidence could not be admitted'))
            command = locals().get('command', {'status':'BLOCKED','exit_code':None})
            if not isinstance(error, Exception): raise
        admitted = finished['result'] in {'PASS','FAIL'}
        receipt_error = None
        if output_guard is not None:
            try:
                output_guard.write_new_json('admission.json', {'execution_id':execution['id'],
                    'admission_status':'ADMITTED' if admitted else 'NOT_ADMITTED',
                    'result':finished['result'],'evidence_refs':finished['evidence_refs'],
                    'raw_result':relative.as_posix()})
            except OSError:
                receipt_error = 'admission receipt unavailable; consult Runtime execution'
        available = output.resolve().is_relative_to(root) and output.is_file()
        return {'execution':finished,'command':command,
                'result_path':relative.as_posix() if admitted else None,
                'unadmitted_result_path':relative.as_posix() if not admitted and available else None,
                'receipt_error':receipt_error}
