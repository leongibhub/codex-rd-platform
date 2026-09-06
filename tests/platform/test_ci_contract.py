"""TASK-V3-006 / NFR-V3-003: CI contract and portable C++ adapter tests."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / '.github' / 'workflows' / 'platform-validation.yml'
VERIFY = ROOT / 'examples' / 'multistack' / 'cpp_inventory' / 'verify.py'


def load_verify_module():
    spec = importlib.util.spec_from_file_location('cpp_inventory_verify', VERIFY)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class CiContractTests(unittest.TestCase):
    def test_workflow_has_required_safety_and_validation_contract(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        for required in ('name: Platform validation', 'push:', 'pull_request:', 'workflow_dispatch:',
                         'permissions:\n  contents: read', 'concurrency:', 'cancel-in-progress: true',
                         'timeout-minutes:', 'actions/checkout@v7', 'actions/setup-python@v7',
                         'tools/mcp/company-context/requirements.txt', 'actions/upload-artifact@v7',
                         "if: ${{ !cancelled() }}"):
            self.assertIn(required, text)
        self.assertNotIn('continue-on-error: true', text)
        self.assertIn('os: [ubuntu-latest, windows-latest]', text)
        self.assertIn("if: runner.os == 'Windows'", text)
        self.assertIn('native g++ is NOT_AVAILABLE', text)
        self.assertIn('$compilerDirectory = Split-Path -Parent $compiler.Source', text)
        self.assertIn('-print-file-name=libstdc++-6.dll', text)
        self.assertIn('native GNU runtime DLL is NOT_AVAILABLE', text)
        self.assertIn('$runtimeDirectory = Split-Path -Parent $runtimeDll', text)
        self.assertIn('@($compilerDirectory, $runtimeDirectory)', text)
        self.assertIn('path: .rd-platform/ci/', text)
        self.assertIn('include-hidden-files: true', text)
        self.assertIn('actions/setup-java@v6', text)
        self.assertEqual(text.count('actions/setup-java@v6'), 2)
        self.assertRegex(text, r"java-version: ['\"]8['\"]")
        self.assertEqual(text.count("java-version: '8'"), 2)
        self.assertNotRegex(text, r"java-version: ['\"]17['\"]")
        self.assertEqual(text.count('actions/setup-node@v7'), 2)
        self.assertEqual(text.count("node-version: '22'"), 2)
        self.assertRegex(text, r"python-version: ['\"]?(?:3\.1[1-9]|[4-9]\.\d+)")
        self.assertIn('python -m venv --copies .venv', text)
        self.assertIn('.venv/Scripts/python.exe', text)
        self.assertIn('.venv/bin/python', text)
        self.assertIn('scripts/write_local_config.py "$GITHUB_WORKSPACE"', text)

    def test_workflow_runs_repository_contracts_and_all_five_manifests(self):
        text = WORKFLOW.read_text(encoding='utf-8')
        for suite in ('tests/runtime', 'tests/platform', 'tests/independent_v3', 'tests/independent_multistack'):
            self.assertIn(suite, text)
        self.assertNotIn('python -m unittest discover', text)
        for app in ('cpp_inventory', 'python_expenses', 'web_notes', 'java_booking', 'wechat_expenses'):
            self.assertIn(f'examples/multistack/{app}/manifest.json', text)
        self.assertIn('stack-run', text)

    def test_cpp_driver_uses_native_argv_off_windows_and_wsl_on_windows(self):
        verify = load_verify_module()
        with patch.object(verify.os, 'name', 'posix'), patch.object(verify.shutil, 'which', return_value='/usr/bin/g++'), patch.object(verify.subprocess, 'run') as run:
            run.return_value.returncode = 0
            verify.invoke(['g++', '--version'])
            self.assertEqual(['g++', '--version'], run.call_args.args[0])
            self.assertEqual(verify.APP, run.call_args.kwargs['cwd'])
        with patch.object(verify.os, 'name', 'nt'), patch.object(verify.shutil, 'which', return_value=None), patch.object(
            verify, 'wsl_path', return_value='/mnt/d/cpp_inventory'
        ) as wsl_path, patch.object(verify.subprocess, 'run') as run:
            run.return_value.returncode = 0
            verify.invoke(['g++', '--version'])
            self.assertEqual('wsl.exe', run.call_args.args[0][0])
            wsl_path.assert_called_once_with(verify.APP)
        with patch.object(verify.os, 'name', 'nt'), patch.object(verify.shutil, 'which', return_value='C:/msys64/ucrt64/bin/g++.exe'), patch.object(verify.subprocess, 'run') as run:
            run.return_value.returncode = 0
            verify.invoke(['g++', '--version'])
            self.assertEqual(['g++', '--version'], run.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
