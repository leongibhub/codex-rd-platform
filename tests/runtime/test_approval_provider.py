"""Integration tests for TASK-V3-017's SSH human-approval adapter.

All keys, signatures, projects and approvals in this module are temporary
fixtures.  They never use the repository's Runtime database.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import subprocess
import tempfile
import unittest
from pathlib import Path

from rd_platform.approval_provider import (
    SshApprovalProvider,
    create_approval_challenge,
    register_signed_approval,
)
from rd_platform.runtime import Runtime
from rd_platform.store import Store


class SshApprovalProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.key = self.root / "operator_ed25519"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(self.key)], check=True, capture_output=True)
        self.allowed = self.root / "allowed_signers"
        public_key = self.key.with_suffix(".pub").read_text(encoding="utf-8").strip()
        self.allowed.write_text("alice namespaces=\"rd-platform-approval\" " + public_key + "\n", encoding="utf-8")
        self.runtime = Runtime(self.root / "state.db")
        self.project = self.runtime.execute("project.create", {"name": "approval fixture", "idea": "temporary only"})["id"]
        self.runtime.execute("agent.register", {"id": "fixture-author", "role": "developer"})
        self.runtime.execute("lifecycle.initialize", {"project_id": self.project, "repository_root": str(self.root), "mode": "active"})
        self.runtime.execute("artifact.create", {
            "project_id": self.project, "artifact_type": "REQ", "artifact_id": "REQ-017",
            "title": "approval fixture", "state": "BASELINED",
            "content_ref": {"inline_json": {"fixture": True}},
            "source": {"kind": "host", "actor": "fixture-author"},
        })
        self.provider = SshApprovalProvider({
            "provider_id": "fixture-ssh", "allowed_signers": str(self.allowed), "ssh_keygen": "ssh-keygen",
            "authorizations": [{"operator": "alice", "projects": [self.project], "gates": ["G9"]}],
        })
        self.runtime = Runtime(self.root / "state.db", approval_provider=self.provider)

    def tearDown(self):
        self.temp.cleanup()

    def approval_data(self, statement="Fixture approval only"):
        return {
            "project_id": self.project, "kind": "human_approval", "status": "VERIFIED",
            "locator": {"inline_json": {"fixture": "temporary"}},
            "observed_at": datetime.now(timezone.utc).isoformat(),
            "metadata": {"gate_id": "G9", "decision": "APPROVE", "statement": statement,
                         "artifact_refs": [{"type": "REQ", "id": "REQ-017", "version": 1}]},
        }

    def signed_response(self, data, *, provider=None, now=None, key=None):
        provider = provider or self.provider
        challenge = create_approval_challenge(self.runtime, data, operator="alice", provider=provider, now=now)
        challenge_path = self.root / ("challenge-" + challenge["verification_id"] + ".json")
        challenge_path.write_text(Store.dumps(challenge), encoding="utf-8")
        subprocess.run(["ssh-keygen", "-Y", "sign", "-f", str(key or self.key), "-n", "rd-platform-approval", str(challenge_path)], check=True, capture_output=True)
        return {"challenge": challenge, "signature_path": str(challenge_path) + ".sig"}

    def test_valid_real_ed25519_signature_registers_through_runtime(self):
        data = self.approval_data()
        approval = register_signed_approval(self.runtime, data, operator="alice", provider=self.provider,
                                            response=self.signed_response(data))
        self.assertEqual("human", approval["recorded_role"])
        self.assertEqual("fixture-ssh", approval["metadata"]["provider_id"])
        self.assertEqual(self.runtime.human_approval_binding(data)["project_id"], self.project)

    def test_rejects_wrong_key_expiry_future_binding_scope_and_replay(self):
        data = self.approval_data()
        other = self.root / "other_ed25519"
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(other)], check=True, capture_output=True)
        with self.assertRaisesRegex(ValueError, "signature"):
            register_signed_approval(self.runtime, data, operator="alice", provider=self.provider,
                                     response=self.signed_response(data, key=other))

        expired = self.signed_response(self.approval_data(), now=datetime.now(timezone.utc) - timedelta(minutes=10))
        with self.assertRaisesRegex(ValueError, "expired"):
            register_signed_approval(self.runtime, self.approval_data(), operator="alice", provider=self.provider, response=expired)

        future = self.signed_response(self.approval_data(), now=datetime.now(timezone.utc) + timedelta(minutes=10))
        with self.assertRaisesRegex(ValueError, "future"):
            register_signed_approval(self.runtime, self.approval_data(), operator="alice", provider=self.provider, response=future)

        signed = self.signed_response(data)
        tampered = self.approval_data(statement="Different statement")
        with self.assertRaisesRegex(ValueError, "binding"):
            register_signed_approval(self.runtime, tampered, operator="alice", provider=self.provider, response=signed)
        approval = register_signed_approval(self.runtime, data, operator="alice", provider=self.provider, response=signed)
        with self.assertRaisesRegex(ValueError, "already been consumed"):
            register_signed_approval(self.runtime, data, operator="alice", provider=self.provider, response=signed)
        self.assertEqual("fixture-ssh", approval["metadata"]["provider_id"])

    def test_rejects_unauthorized_scope_agent_identity_and_stale_binding(self):
        data = self.approval_data()
        no_gate = SshApprovalProvider({
            "provider_id": "scope-fixture", "allowed_signers": str(self.allowed), "ssh_keygen": "ssh-keygen",
            "authorizations": [{"operator": "alice", "projects": [self.project], "gates": ["G10"]}],
        })
        with self.assertRaisesRegex(ValueError, "authorized"):
            create_approval_challenge(self.runtime, data, operator="alice", provider=no_gate)

        signed = self.signed_response(data)
        self.runtime.execute("agent.register", {"id": "alice", "role": "reviewer"})
        with self.assertRaisesRegex(ValueError, "agent identity"):
            register_signed_approval(self.runtime, data, operator="alice", provider=self.provider, response=signed)

        # A changed artifact version invalidates the originally bound approval.
        self.runtime.execute("artifact.revise", {
            "artifact_id": "REQ-017", "expected_version": 1, "state": "BASELINED",
            "content_ref": {"inline_json": {"fixture": "changed"}}, "reason": "fixture mutation", "material": False,
        })
        with self.assertRaises(ValueError):
            self.runtime.human_approval_binding(data)


if __name__ == "__main__":
    unittest.main()
