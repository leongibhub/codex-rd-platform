"""Opt-in live no-tools proposal smoke. No unsafe Codex execution fallback."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rd_platform.runtime import Runtime
from rd_platform.worker_service import run_service


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute-real-model', action='store_true', required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--api-key-env', default='OPENAI_API_KEY')
    args = parser.parse_args()
    if not os.environ.get(args.api_key_env):
        print(json.dumps({'status': 'NOT_AVAILABLE', 'reason': 'API credential is not configured',
                          'real_api_executed': False}))
        return 2
    base = Path(tempfile.mkdtemp(prefix='rd-platform-safe-worker-'))
    root = base / 'application'
    root.mkdir()
    subprocess.run(['git', 'init', '--quiet', str(root)], check=True, capture_output=True)
    runtime = Runtime(base / 'control.db')
    project = runtime.execute('project.create', {'name': 'Live proposal smoke', 'idea': 'Offline text statistics CLI'})['id']
    runtime.execute('lifecycle.initialize', {'project_id': project, 'repository_root': str(root), 'mode': 'active'})
    runtime.execute('agent.register', {'id': 'live-proposal-developer', 'role': 'developer'})
    requirement = (
        'Create app.py and test_app.py using Python standard library only. app.py FILE reads UTF-8 and prints '
        'a JSON object with lines=len(text.splitlines()), words=len(text.split()), characters=len(text). '
        'Empty input gives zero counts. Missing file and invalid UTF-8 exit nonzero with stderr, no success JSON. '
        'Generate unittest tests for normal, Unicode, empty, missing and invalid UTF-8 public CLI input. '
        'You have no execution tools: do not claim you ran tests. The trusted host will run them separately. '
        'Return create proposals with expected_sha256=null, CODE-LIVE-APP and CODE-LIVE-TEST of type CODE_CHANGE. '
        'Do not propose credentials, network access, control metadata, dependencies or approval records.'
    )
    work = runtime.execute('work.create', {'project_id': project, 'gate_id': 'G6',
        'activity': 'Generate offline text statistics app', 'why': requirement,
        'required_role': 'developer', 'input_refs': [], 'dependencies': [],
        'output_contract': {'required_types': ['CODE_CHANGE'], 'min_outputs': 2}})
    config = {'project_id': project, 'repository_root': str(root), 'max_concurrency': 1,
        'workers': [{'agent_id': 'live-proposal-developer', 'role': 'developer',
            'source_paths': ['app.py', 'test_app.py'], 'lease_seconds': 300, 'timeout_seconds': 180, 'max_output_bytes': 500000,
            'backend': {'type': 'responses', 'model': args.model, 'api_key_env': args.api_key_env,
                        'max_output_tokens': 8192}}]}
    outcome = run_service(runtime, config, once=True)
    # Host inspection is required before executing arbitrary newly generated code.
    report = {'status': 'PROPOSALS_ADMITTED' if outcome['completed'] == 1 else 'FAIL',
        'scope': 'live_no_tools_proposal_transport_and_admission_only',
        'project_id': project, 'work_id': work['id'], 'workspace': str(root), 'result': outcome,
        'host_test_command': [sys.executable, '-m', 'unittest', '-v', 'test_app'],
        'host_tests': 'NOT_EXECUTED', 'independent_review': 'NOT_EXECUTED',
        'human_approval': 'NOT_AVAILABLE', 'production_deployment': 'NOT_EXECUTED'}
    with (base / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False), flush=True)
    return 0 if outcome['completed'] == 1 else 1


if __name__ == '__main__':
    raise SystemExit(main())
