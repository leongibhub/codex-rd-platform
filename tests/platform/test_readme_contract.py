"""Independent executable README contract checks for TASK-V3-009.

These are documentation/CLI contract checks, not a fresh-clone, global setup,
browser, native-WeChat, or hosted-agent end-to-end test.
"""
from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[2]
READMES = (ROOT / "README.md", ROOT / "README.en.md")
BRANCH = "codex/platform-v3-lifecycle"


class ReadmeContractTests(unittest.TestCase):
    """TC-V3-README-001..005 / TASK-V3-009, NFR-V3-004/005."""

    @staticmethod
    def text(path: Path) -> str:
        return path.read_text(encoding="utf-8")

    def git(self, *arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *arguments], cwd=cwd, text=True, encoding="utf-8",
            capture_output=True, timeout=30, check=False,
        )

    def feature_remote(self, temporary: Path) -> tuple[str, Path]:
        """Create a disposable remote with main and the README feature branch."""
        source, remote = temporary / "source", temporary / "remote.git"
        for command in (("init", str(source)),
                        ("-C", str(source), "config", "user.name", "fixture"),
                        ("-C", str(source), "config", "user.email", "fixture@example.test")):
            completed = self.git(*command)
            self.assertEqual(0, completed.returncode, completed.stderr)
        (source / "fixture.txt").write_text("main\n", encoding="utf-8")
        for command in (("-C", str(source), "add", "fixture.txt"),
                        ("-C", str(source), "commit", "-m", "main fixture"),
                        ("-C", str(source), "branch", "-M", "main"),
                        ("-C", str(source), "switch", "-c", BRANCH)):
            completed = self.git(*command)
            self.assertEqual(0, completed.returncode, completed.stderr)
        (source / "fixture.txt").write_text("feature\n", encoding="utf-8")
        for command in (("-C", str(source), "commit", "-am", "feature fixture"),
                        ("-C", str(source), "switch", "main"),
                        ("clone", "--bare", str(source), str(remote))):
            completed = self.git(*command)
            self.assertEqual(0, completed.returncode, completed.stderr)
        return remote.as_uri(), source

    def test_tc_v3_readme_001_all_local_markdown_links_resolve(self) -> None:
        """Usability: each relative Markdown document link in both guides exists."""
        pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")
        for readme in READMES:
            with self.subTest(readme=readme.name):
                missing = []
                for raw in pattern.findall(self.text(readme)):
                    target = raw.split("#", 1)[0].strip().strip("<>")
                    if not target or "://" in target or target.startswith("mailto:"):
                        continue
                    if not (ROOT / target).is_file():
                        missing.append(target)
                self.assertEqual([], missing)

    def test_tc_v3_readme_002_documented_routes_are_present_in_real_cli_help(self) -> None:
        """CLI contract: documented report/export/test routes are actually discoverable."""
        result = subprocess.run(
            [sys.executable, "-m", "rd_platform", "--help"], cwd=ROOT,
            text=True, encoding="utf-8", capture_output=True, timeout=20, check=False,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        for command in ("snapshot", "lifecycle", "lifecycle-collection", "lifecycle-report", "project-export", "test-run", "stack-probe", "run"):
            self.assertIn(command, result.stdout)
        for readme in READMES:
            content = self.text(readme)
            for command in ("lifecycle-report", "project-export", "test-run", "stack-probe"):
                self.assertIn(command, content, f"{readme.name} omits {command}")
        for command, required in (("lifecycle-report", "--project-id"), ("project-export", "--output-dir"), ("test-run", "--case-version")):
            route = subprocess.run(
                [sys.executable, "-m", "rd_platform", command, "--help"], cwd=ROOT,
                text=True, encoding="utf-8", capture_output=True, timeout=20, check=False,
            )
            self.assertEqual(0, route.returncode, route.stderr)
            self.assertIn(required, route.stdout)

    def test_tc_v3_readme_003_setup_dependency_clone_and_feature_branch_contract(self) -> None:
        """Compatibility: guides name clone source/branch and files, not this runner's Git remote state."""
        self.assertTrue((ROOT / "scripts" / "setup.ps1").is_file())
        self.assertTrue((ROOT / "scripts" / "validate_platform.py").is_file())
        self.assertTrue((ROOT / "tools" / "mcp" / "company-context" / "requirements.txt").is_file())
        for readme in READMES:
            content = self.text(readme)
            self.assertRegex(content, re.compile(
                r"git clone --branch " + re.escape(BRANCH) +
                r" --single-branch https://github\.com/leongibhub/codex-rd-platform\.git"
            ))
            self.assertIn("git remote set-branches --add origin " + BRANCH, content)
            self.assertIn("git fetch origin", content)
            self.assertIn("git show-ref --verify --quiet refs/heads/" + BRANCH, content)
            self.assertIn("git switch --track -c " + BRANCH + " origin/" + BRANCH, content)
            self.assertIn("git merge --ff-only origin/" + BRANCH, content)
            self.assertIn("tools/mcp/company-context/requirements.txt", content)
            self.assertIn("setup.ps1", content)
            self.assertRegex(content, r"Python 3\.11\+|Python 3\.11 or newer")

        # A CI PR/shallow checkout can have a different origin (or none) and
        # not advertise this feature ref.  The guide must be judged from its
        # documented clone command and files, never from the host checkout.
        with tempfile.TemporaryDirectory(prefix="readme-shallow-") as temporary:
            source = Path(temporary) / "source"
            clone = Path(temporary) / "clone"
            for command in (
                ["git", "init", str(source)],
                ["git", "-C", str(source), "-c", "user.name=fixture", "-c", "user.email=fixture@example.test", "commit", "--allow-empty", "-m", "fixture"],
                ["git", "-C", str(source), "branch", "-M", "main"],
                ["git", "clone", "--depth", "1", "--single-branch", "--branch", "main", source.as_uri(), str(clone)],
            ):
                completed = subprocess.run(command, text=True, encoding="utf-8", capture_output=True, timeout=20, check=False)
                self.assertEqual(0, completed.returncode, completed.stderr)
            shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"], cwd=clone, text=True, encoding="utf-8", capture_output=True, timeout=20, check=False)
            remote = subprocess.run(["git", "remote", "get-url", "origin"], cwd=clone, text=True, encoding="utf-8", capture_output=True, timeout=20, check=False)
            branch = subprocess.run(["git", "branch", "-r", "--list", "origin/" + BRANCH], cwd=clone, text=True, encoding="utf-8", capture_output=True, timeout=20, check=False)
            self.assertEqual((0, "true"), (shallow.returncode, shallow.stdout.strip()))
            self.assertEqual(0, remote.returncode, remote.stderr)
            self.assertNotEqual("https://github.com/leongibhub/codex-rd-platform.git", remote.stdout.strip())
            self.assertEqual("", branch.stdout.strip())

    def test_tc_v3_readme_005_feature_branch_continuation_uses_remote_mapping_and_handles_local_branch(self) -> None:
        """Regression: old fetch-only flow REDs; documented mapping works in three clone states."""
        with tempfile.TemporaryDirectory(prefix="readme-git-") as temporary:
            temporary_root = Path(temporary)
            remote, source = self.feature_remote(temporary_root)
            fresh, main_only, existing = (temporary_root / name for name in ("fresh", "main-only", "existing"))

            first = self.git("clone", "--branch", BRANCH, "--single-branch", remote, str(fresh))
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(BRANCH, self.git("branch", "--show-current", cwd=fresh).stdout.strip())

            clone = self.git("clone", "--depth", "1", "--single-branch", "--branch", "main", remote, str(main_only))
            self.assertEqual(0, clone.returncode, clone.stderr)
            old_fetch = self.git("fetch", "origin", BRANCH, cwd=main_only)
            old_switch = self.git("switch", "--track", "origin/" + BRANCH, cwd=main_only)
            self.assertEqual(0, old_fetch.returncode, old_fetch.stderr)
            self.assertNotEqual(0, old_switch.returncode, "old flow unexpectedly created the missing remote tracking ref")
            self.assertEqual("", self.git("branch", "-r", "--list", "origin/" + BRANCH, cwd=main_only).stdout.strip())

            mapping = self.git("remote", "set-branches", "--add", "origin", BRANCH, cwd=main_only)
            self.assertEqual(0, mapping.returncode, mapping.stderr)
            corrected = self.git("fetch", "origin", cwd=main_only)
            self.assertEqual(0, corrected.returncode, corrected.stderr)
            self.assertEqual(0, self.git("show-ref", "--verify", "--quiet", "refs/remotes/origin/" + BRANCH, cwd=main_only).returncode)
            switched = self.git("switch", "--track", "-c", BRANCH, "origin/" + BRANCH, cwd=main_only)
            self.assertEqual(0, switched.returncode, switched.stderr)
            self.assertEqual("origin/" + BRANCH, self.git("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}", cwd=main_only).stdout.strip())

            cloned_existing = self.git("clone", "--depth", "1", "--single-branch", "--branch", "main", remote, str(existing))
            self.assertEqual(0, cloned_existing.returncode, cloned_existing.stderr)
            self.assertEqual(0, self.git("branch", BRANCH, cwd=existing).returncode)

            # The local branch exists before the remote moves.  The README's
            # existing-branch path must therefore update it, not merely avoid
            # the "already exists" error.
            self.assertEqual(0, self.git("switch", BRANCH, cwd=source).returncode)
            (source / "fixture.txt").write_text("feature newer\n", encoding="utf-8")
            self.assertEqual(0, self.git("add", "fixture.txt", cwd=source).returncode)
            self.assertEqual(0, self.git("commit", "-m", "feature newer", cwd=source).returncode)
            pushed = self.git("push", remote, BRANCH, cwd=source)
            self.assertEqual(0, pushed.returncode, pushed.stderr)

            mapping_existing = self.git("remote", "set-branches", "--add", "origin", BRANCH, cwd=existing)
            self.assertEqual(0, mapping_existing.returncode, mapping_existing.stderr)
            fetched_existing = self.git("fetch", "origin", cwd=existing)
            self.assertEqual(0, fetched_existing.returncode, fetched_existing.stderr)
            remote_tip = self.git("rev-parse", "origin/" + BRANCH, cwd=existing)
            self.assertEqual(0, remote_tip.returncode, remote_tip.stderr)
            local_before = self.git("rev-parse", BRANCH, cwd=existing)
            self.assertEqual(0, local_before.returncode, local_before.stderr)
            self.assertNotEqual(remote_tip.stdout.strip(), local_before.stdout.strip())
            continued = self.git("switch", BRANCH, cwd=existing)
            self.assertEqual(0, continued.returncode, continued.stderr)
            merged = self.git("merge", "--ff-only", "origin/" + BRANCH, cwd=existing)
            self.assertEqual(0, merged.returncode, merged.stderr)
            self.assertEqual(BRANCH, self.git("branch", "--show-current", cwd=existing).stdout.strip())
            self.assertEqual(remote_tip.stdout.strip(), self.git("rev-parse", "HEAD", cwd=existing).stdout.strip())

    def test_tc_v3_readme_004_local_host_and_native_boundaries_are_explicit(self) -> None:
        """Safety: documentation must not turn self-host prompts or Node adapters into unsupported services/native evidence."""
        chinese, english = (self.text(path) for path in READMES)
        for content in (chinese, english):
            self.assertIn("platform-orchestration", content)
            self.assertIn("lifecycle-report", content)
            self.assertIn("project-export", content)
        self.assertIn("不是自动调用模型的云服务", chinese)
        self.assertIn("Skill 是工作方法约束而不是服务启动器", chinese)
        self.assertIn("微信原生", chinese)
        self.assertIn("Node fake-wx 不替代", chinese)
        self.assertIn("NOT_AVAILABLE", chinese)
        self.assertIn("not a model-calling cloud service", english)
        self.assertIn("not a service launcher", english)
        self.assertIn("WeChat native", english)
        self.assertIn("Node fake-wx is not a substitute", english)
        self.assertIn("NOT_AVAILABLE", english)
        self.assertIn("已登记为 tester 的 `executor-id`", chinese)
        self.assertIn("不是身份认证", chinese)
        self.assertIn("不会模拟另一个 OS 用户", chinese)
        self.assertIn("declared by the trusted host and registered as a tester", english)
        self.assertIn("not identity authentication", english)
        self.assertIn("does not impersonate another OS user", english)


if __name__ == "__main__":
    unittest.main(verbosity=2)
