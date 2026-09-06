# SSH Ed25519 approval provider

Traceability: `REQ-V3-017`, `DES-V3-003`, `TASK-V3-017`.

`SshApprovalProvider` is an optional, trusted-host adapter for the existing
`Runtime.register_human_approval` channel. The default `Runtime` still has no
provider and rejects human-approval registration with `NOT_AVAILABLE`.

The adapter verifies an OpenSSH Ed25519 signature. It proves control of an
authorized signing key for one exact, current Runtime binding; it does not
prove customer satisfaction or create a Gate decision. A challenge is only a
request to sign, never an approval record.

## Protected host configuration

Keep this configuration and `allowed_signers` in an operator-protected local
directory, outside Git. The private key stays with the human operator and is
never supplied to Python, configuration, Git, Runtime evidence, or command
output.

```python
from rd_platform.approval_provider import SshApprovalProvider
from rd_platform.runtime import Runtime

provider = SshApprovalProvider({
    "provider_id": "corp-approval-ssh-2026",
    "allowed_signers": r"D:\secure\approval\allowed_signers",
    "ssh_keygen": r"C:\Windows\System32\OpenSSH\ssh-keygen.exe",
    "authorizations": [
        {"operator": "approved-operator", "projects": ["project-real-id"], "gates": ["G9", "G10", "G11"]}
    ],
    "challenge_ttl_seconds": 300,
    "timeout_seconds": 10,
    "max_output_bytes": 4096,
})
runtime = Runtime(".rd-platform/state.db", approval_provider=provider)
```

Each authorization is exact: one operator plus nonempty project and Gate
allowlists. The constructor rejects unknown configuration fields, missing or
symlinked signer files, unavailable executables, duplicate operator rules, and
invalid budget values. The signers file must use OpenSSH `allowed_signers`
format and restrict the namespace `rd-platform-approval`, for example:

```text
approved-operator namespaces="rd-platform-approval" ssh-ed25519 AAAA... public-comment
```

Only a public key appears in this file. Treat the configuration directory as
trusted host administration, not an untrusted multi-tenant boundary.

## Trusted CLI integration contract

CLI integration belongs to `TASK-V3-020`; this task intentionally does not
modify `cli.py` or HTTP. The primary integration can expose two trusted local
operations using these public helpers:

```python
from rd_platform.approval_provider import create_approval_challenge, register_signed_approval

challenge = create_approval_challenge(runtime, approval_data,
    operator="approved-operator", provider=provider)
# Serialize exactly Store.dumps(challenge) as UTF-8 to CHALLENGE.json.
# The human signs outside the platform:
# ssh-keygen -Y sign -f PATH_TO_PRIVATE_ED25519_KEY -n rd-platform-approval CHALLENGE.json

approval = register_signed_approval(runtime, approval_data,
    operator="approved-operator", provider=provider,
    response={"challenge": challenge, "signature_path": "CHALLENGE.json.sig"})
```

`Runtime.human_approval_binding(approval_data)` is a public read-only helper
for displaying or preflighting the current exact scope. It computes the same
binding used by registration and writes no evidence. `approval_data` remains
the established human-approval request shape: `kind=human_approval`,
`status=VERIFIED`, a timezone-aware nonfuture observation time, and metadata
with `gate_id`, `decision`, `statement`, and current `artifact_refs`.

The signed challenge contains a random nonce and verification ID, issue and
expiry timestamps, operator, provider ID, project ID, Gate ID, and the
canonical Runtime binding digest. The binding itself includes the decision,
statement, locked subject versions/digests, policy version, and current policy
input digest. Verification re-computes it at submission time.

The verifier launches only the configured `ssh-keygen` with explicit argv,
`shell=False`, a finite timeout, and a bounded combined output stream. It
rejects wrong keys, expired or future challenges, malformed or changed
challenges, signer/project/Gate scope mismatch, output-budget excess, and a
nonzero OpenSSH verification result. `Runtime` independently rejects a claimed
operator that is a registered Agent, requires the provider-returned binding
digest and identity to match, and consumes each `(provider_id, verification_id)`
at most once. A changed artifact/policy binding no longer validates an older
challenge.

Do not log a private key, private-key path, passphrase, signed URL, token, or
raw secret in CLI output, evidence, test fixtures, or Git. Use isolated
temporary test keys only for automated tests; they are not human-approval or
acceptance evidence for this repository.

## Developer verification

The scoped test generates temporary Ed25519 fixture keys, executes real
`ssh-keygen -Y sign` and `-Y verify`, and submits the valid signature through
an isolated Runtime database. It also covers wrong key, expiry, future issue
time, binding tamper, authorization scope, registered-Agent identity, replay,
and stale artifact binding rejection.

```powershell
.\.venv\Scripts\python.exe -X utf8 -m unittest tests.runtime.test_approval_provider -v
```

This is developer/unit verification only. Independent testing, review, actual
human approval, Gate decision, and production acceptance remain separate.
