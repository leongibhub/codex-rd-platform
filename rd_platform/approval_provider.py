"""SSH Ed25519 authentication adapter for the trusted human-approval channel.

The adapter verifies an externally-created OpenSSH signature.  It deliberately
does not own, load, or generate a private key, and it is not installed as the
Runtime default provider.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
from pathlib import Path
import secrets
import shutil
import subprocess
import threading
import time
from typing import Any

from .store import Store


NAMESPACE = "rd-platform-approval"
CHALLENGE_VERSION = "ssh-ed25519-approval-v1"


def _text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(label + " must be non-empty text")
    return value.strip()


def _digest(value: object) -> str:
    return hashlib.sha256(Store.dumps(value).encode("utf-8")).hexdigest()


def _time(value: object, label: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(label + " must be an ISO-8601 timestamp")
    try:
        result = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(label + " must be an ISO-8601 timestamp") from error
    if result.tzinfo is None:
        raise ValueError(label + " must include a timezone")
    return result.astimezone(timezone.utc)


class SshApprovalProvider:
    """Verify scope-bound OpenSSH signatures against fixed local trust config."""

    def __init__(self, config: dict[str, Any]):
        if not isinstance(config, dict):
            raise ValueError("approval provider config must be an object")
        allowed = {"provider_id", "allowed_signers", "ssh_keygen", "authorizations", "timeout_seconds", "max_output_bytes", "challenge_ttl_seconds"}
        if set(config) - allowed:
            raise ValueError("unknown approval provider configuration")
        self.provider_id = _text(config.get("provider_id"), "provider_id")
        signers = Path(_text(config.get("allowed_signers"), "allowed_signers")).resolve(strict=True)
        if not signers.is_file() or signers.is_symlink():
            raise ValueError("allowed_signers must be a regular protected file")
        self.allowed_signers = signers
        executable = _text(config.get("ssh_keygen"), "ssh_keygen")
        resolved_executable = shutil.which(executable) if not Path(executable).is_file() else executable
        if not resolved_executable:
            raise ValueError("ssh_keygen executable is unavailable")
        self.ssh_keygen = str(Path(resolved_executable).resolve(strict=True))
        self.timeout_seconds = self._number(config.get("timeout_seconds", 10), "timeout_seconds", 0.1, 60)
        self.max_output_bytes = self._integer(config.get("max_output_bytes", 4096), "max_output_bytes", 1, 65536)
        self.challenge_ttl_seconds = self._integer(config.get("challenge_ttl_seconds", 300), "challenge_ttl_seconds", 1, 3600)
        authorizations = config.get("authorizations")
        if not isinstance(authorizations, list) or not authorizations:
            raise ValueError("authorizations must be a non-empty list")
        self.authorizations: dict[str, tuple[frozenset[str], frozenset[str]]] = {}
        for row in authorizations:
            if not isinstance(row, dict) or set(row) != {"operator", "projects", "gates"}:
                raise ValueError("authorization must contain operator, projects and gates")
            operator = _text(row.get("operator"), "authorized operator")
            projects = self._strings(row.get("projects"), "authorized projects")
            gates = self._strings(row.get("gates"), "authorized gates")
            if any(gate not in {"G" + str(index) for index in range(12)} for gate in gates):
                raise ValueError("authorized gates must be G0 through G11")
            if operator in self.authorizations:
                raise ValueError("duplicate operator authorization")
            self.authorizations[operator] = (frozenset(projects), frozenset(gates))
        signer_lines = self.allowed_signers.read_text(encoding="utf-8").splitlines()
        for operator in self.authorizations:
            matching = [line.split() for line in signer_lines if line.strip() and not line.lstrip().startswith("#") and line.split()[0] == operator]
            if not any("ssh-ed25519" in fields and any(NAMESPACE in field for field in fields) for fields in matching):
                raise ValueError("each authorized operator requires an Ed25519 namespaced allowed signer")

    @staticmethod
    def _integer(value: object, label: str, low: int, high: int) -> int:
        if type(value) is not int or not low <= value <= high:
            raise ValueError("invalid " + label)
        return value

    @staticmethod
    def _number(value: object, label: str, low: float, high: float) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not low <= value <= high:
            raise ValueError("invalid " + label)
        return float(value)

    @staticmethod
    def _strings(value: object, label: str) -> list[str]:
        if not isinstance(value, list) or not value or any(not isinstance(item, str) or not item.strip() for item in value):
            raise ValueError(label + " must be a non-empty list of strings")
        result = [item.strip() for item in value]
        if len(set(result)) != len(result):
            raise ValueError(label + " must not contain duplicates")
        return result

    def _authorize(self, operator: str, binding: dict[str, Any]) -> None:
        scope = self.authorizations.get(operator)
        if scope is None or binding.get("project_id") not in scope[0] or binding.get("gate_id") not in scope[1]:
            raise ValueError("operator is not authorized for this project and Gate")

    def create_challenge(self, *, binding: dict[str, Any], operator: str, now: datetime | None = None) -> dict[str, Any]:
        if not isinstance(binding, dict):
            raise ValueError("approval binding must be an object")
        operator = _text(operator, "operator")
        self._authorize(operator, binding)
        clock = now or datetime.now(timezone.utc)
        if clock.tzinfo is None:
            raise ValueError("challenge time must include a timezone")
        issued = clock.astimezone(timezone.utc)
        expires = issued + timedelta(seconds=self.challenge_ttl_seconds)
        return {
            "version": CHALLENGE_VERSION,
            "provider_id": self.provider_id,
            "verification_id": secrets.token_urlsafe(32),
            "nonce": secrets.token_urlsafe(32),
            "issued_at": issued.isoformat(),
            "expires_at": expires.isoformat(),
            "operator": operator,
            "project_id": binding["project_id"],
            "gate_id": binding["gate_id"],
            "binding_digest": _digest(binding),
        }

    def verify(self, *, binding: dict[str, Any], approval_request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(binding, dict) or not isinstance(approval_request, dict):
            raise ValueError("approval verification inputs must be objects")
        response = approval_request.get("approval_response")
        if not isinstance(response, dict) or set(response) != {"challenge", "signature_path"}:
            raise ValueError("signed approval response is required")
        challenge = response["challenge"]
        if not isinstance(challenge, dict):
            raise ValueError("approval challenge must be an object")
        expected = {"version", "provider_id", "verification_id", "nonce", "issued_at", "expires_at", "operator", "project_id", "gate_id", "binding_digest"}
        if set(challenge) != expected:
            raise ValueError("approval challenge fields are invalid")
        if challenge["version"] != CHALLENGE_VERSION or challenge["provider_id"] != self.provider_id:
            raise ValueError("approval challenge provider is invalid")
        verification_id = _text(challenge["verification_id"], "verification_id")
        _text(challenge["nonce"], "challenge nonce")
        operator = _text(challenge["operator"], "challenge operator")
        self._authorize(operator, binding)
        if challenge["project_id"] != binding.get("project_id") or challenge["gate_id"] != binding.get("gate_id") or challenge["binding_digest"] != _digest(binding):
            raise ValueError("approval challenge binding does not match current request")
        issued, expires, current = _time(challenge["issued_at"], "issued_at"), _time(challenge["expires_at"], "expires_at"), datetime.now(timezone.utc)
        if issued > current:
            raise ValueError("approval challenge is from the future")
        if expires <= issued or expires - issued > timedelta(seconds=self.challenge_ttl_seconds) or expires < current:
            raise ValueError("approval challenge has expired")
        signature = Path(_text(response["signature_path"], "signature_path")).resolve(strict=True)
        if not signature.is_file() or signature.is_symlink() or signature.stat().st_size > 65536:
            raise ValueError("approval signature file is invalid")
        return self._verify_with_challenge(operator, verification_id, challenge, signature, binding)

    def _verify_with_challenge(self, operator: str, verification_id: str, challenge: dict[str, Any], signature: Path, binding: dict[str, Any]) -> dict[str, Any]:
        """Use a bounded, shell-free pipe because OpenSSH requires signed bytes on stdin."""
        try:
            process = subprocess.Popen(
                [self.ssh_keygen, "-Y", "verify", "-f", str(self.allowed_signers), "-I", operator, "-n", NAMESPACE, "-s", str(signature)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False, cwd=self.allowed_signers.parent,
            )
        except OSError as error:
            raise ValueError("ssh approval verification could not start") from error
        output = bytearray()
        exceeded = threading.Event()

        def drain() -> None:
            while chunk := process.stdout.read(4096):
                if len(output) + len(chunk) > self.max_output_bytes:
                    exceeded.set()
                    process.kill()
                    return
                output.extend(chunk)

        reader = threading.Thread(target=drain, daemon=True)
        try:
            process.stdin.write(Store.dumps(challenge).encode("utf-8"))
            process.stdin.close()
            reader.start()
            deadline = time.monotonic() + self.timeout_seconds
            while process.poll() is None and not exceeded.is_set() and time.monotonic() < deadline:
                time.sleep(0.01)
            if process.poll() is None:
                process.kill()
                if exceeded.is_set():
                    raise ValueError("ssh approval verification exceeded output budget")
                raise ValueError("ssh approval verification timed out")
            reader.join(timeout=1)
        finally:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=5)
            process.stdout.close()
        if exceeded.is_set():
            raise ValueError("ssh approval verification exceeded output budget")
        if process.returncode != 0:
            raise ValueError("ssh approval signature verification failed")
        return {"authenticated": True, "operator": operator, "provider_id": self.provider_id,
                "verification_id": verification_id, "binding_digest": _digest(binding)}


def create_approval_challenge(runtime, approval_data: dict[str, Any], *, operator: str, provider: SshApprovalProvider,
                              now: datetime | None = None) -> dict[str, Any]:
    """Create data for an external ``ssh-keygen -Y sign`` invocation; this is not approval."""
    if not isinstance(provider, SshApprovalProvider):
        raise ValueError("SshApprovalProvider is required")
    return provider.create_challenge(binding=runtime.human_approval_binding(approval_data), operator=operator, now=now)


def register_signed_approval(runtime, approval_data: dict[str, Any], *, operator: str, provider: SshApprovalProvider,
                             response: dict[str, Any]) -> dict[str, Any]:
    """Submit one external signature through the existing trusted Runtime method."""
    if runtime.approval_provider is not provider:
        raise ValueError("Runtime must be constructed with this approval provider")
    if not isinstance(approval_data, dict) or "approval_response" in approval_data:
        raise ValueError("approval data must be an unsigned approval request")
    request = dict(approval_data, approval_response=response)
    return runtime.register_human_approval(request, operator=operator)
