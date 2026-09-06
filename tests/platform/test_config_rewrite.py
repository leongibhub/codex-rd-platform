from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import tomllib
import importlib.util
from unittest.mock import patch
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "write_local_config.py"


class ConfigRewriteTests(unittest.TestCase):
    def test_failed_postcondition_leaves_file_byte_identical(self):
        spec = importlib.util.spec_from_file_location('tested_config_rewrite', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        original = ('dummy_command = "decoy-one"\r\ndummy_args = ["decoy-two"]\r\ndummy_cwd = "decoy-three"\r\n'
                    '[mcp_servers.company_context]\r\ncommand = "old"\r\nargs = ["old"]\r\ncwd = "old"\r\n')
        wrong_spans = {}
        for key, token in [('command', '"decoy-one"'), ('args', '["decoy-two"]'), ('cwd', '"decoy-three"')]:
            start = original.index(token)
            wrong_spans[key] = (start, start + len(token))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = self._write_config(root, original)
            with patch.object(module, '_launch_spans', return_value=wrong_spans), patch.object(sys, 'argv', [str(SCRIPT), str(root)]):
                with self.assertRaises(SystemExit) as raised:
                    module.main()
            self.assertEqual(raised.exception.code, 2)
            self.assertEqual(config.read_bytes(), original.encode())

    def test_multiline_fake_keys_headers_crlf_and_indented_real_header(self):
        for header in ('[mcp_servers.company_context]', '  [mcp_servers.company_context] # launch'):
            original = ('description = """\r\n[mcp_servers.company_context]\r\ncommand = \'fake\'\r\nargs = [\'fake\']\r\ncwd = \'fake\'\r\n"""\r\n'
                        + header + '\r\ndescription = \'\'\'\r\ncommand = "fake-inner"\r\nargs = ["fake-inner"]\r\ncwd = "fake-inner"\r\n[another.fake]\r\n\'\'\'\r\ncommand = "old" # keep\r\nargs = ["old"]\r\ncwd = "old"\r\n  [mcp_servers.other] # preserve\r\ncommand = "other"\r\n')
            with self.subTest(header=header), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                config = self._write_config(root, original)
                result = self._run(root)
                self.assertEqual(result.returncode, 0, result.stderr)
                rewritten = config.read_bytes().decode()
                parsed = tomllib.loads(rewritten)
                target = parsed['mcp_servers']['company_context']
                self.assertEqual(target['command'], str(root / '.venv' / 'Scripts' / 'python.exe'))
                self.assertEqual(target['args'], [str(root / 'tools' / 'mcp' / 'company-context' / 'server.py')])
                self.assertEqual(target['cwd'], str(root))
                self.assertEqual(target['description'], tomllib.loads(original)['mcp_servers']['company_context']['description'])
                self.assertEqual(parsed['description'], tomllib.loads(original)['description'])
                self.assertEqual(rewritten.split('  [mcp_servers.other]')[1], original.split('  [mcp_servers.other]')[1])
                self.assertNotIn('\n', rewritten.replace('\r\n', ''))

    def _write_config(self, root: Path, text: str) -> Path:
        config = root / ".codex" / "config.toml"
        config.parent.mkdir()
        config.write_bytes(text.encode("utf-8"))
        return config

    def _run(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(root)],
            text=True,
            capture_output=True,
            check=False,
        )

    def test_rewrites_only_company_context_and_preserves_other_mcp_bytes(self) -> None:
        original = (
            "[mcp_servers.other_mcp]\n"
            "command = \"other-python\"\n"
            "args = [\n"
            "  \"--serve\",\n"
            "  \"other-server.py\",\n"
            "]\n"
            "cwd = \"C:/other\"\n"
            "enabled = true\n\n"
            "[mcp_servers.company_context]\n"
            "command = \"old-python\"\n"
            "args = [\"old-server.py\"]\n"
            "cwd = \"C:/old\"\n"
            "required = true\n\n"
            "[mcp_servers.trailing]\n"
            "url = \"https://example.test/mcp\"\n"
        )
        other_before, company_and_after = original.split("[mcp_servers.company_context]", 1)
        company_before, after_before = company_and_after.split("[mcp_servers.trailing]", 1)

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config = self._write_config(root, original)
            result = self._run(root)
            rewritten = config.read_bytes().decode("utf-8")

        self.assertEqual(result.returncode, 0, result.stderr)
        other_after, company_and_after = rewritten.split("[mcp_servers.company_context]", 1)
        company_after, after_after = company_and_after.split("[mcp_servers.trailing]", 1)
        self.assertEqual(other_after, other_before)
        self.assertEqual(after_after, after_before)
        self.assertIn('command = "', company_after)
        self.assertIn('args = ["', company_after)
        self.assertIn('cwd = "', company_after)
        self.assertIn("required = true", company_after)

    def test_missing_or_invalid_target_rejects_without_changing_file(self) -> None:
        cases = (
            "[mcp_servers.other_mcp]\ncommand = \"python\"\nargs = [\"server.py\"]\ncwd = \".\"\n",
            "[mcp_servers.company_context]\ncommand = 42\nargs = [\"server.py\"]\ncwd = \".\"\n",
        )
        for original in cases:
            with self.subTest(original=original), tempfile.TemporaryDirectory() as temp_dir:
                root = Path(temp_dir)
                config = self._write_config(root, original)
                result = self._run(root)

                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(config.read_bytes(), original.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
