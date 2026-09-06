# TASK-V2-004 Compatibility Implementation Record

- Task: `TASK-V2-004`
- Requirement: `REQ-V2-010`
- Design: `DES-V2-001`; launch-path decision: `ADR-003`
- Scope: `scripts/write_local_config.py`, `tests/platform/test_config_rewrite.py`, and `.codex/agents/documentation-manager.toml`.

## Change summary

`write_local_config.py` now parses the complete TOML document before editing and limits replacements to the unique `[mcp_servers.company_context]` section. It replaces only that section's `command`, `args`, and `cwd` values. Other sections retain their original bytes, including a second MCP's multiline `args` array.

The script rejects a missing, malformed, or type-invalid company-context target before writing. A successful rewrite is TOML-parsed again and is persisted through a same-directory temporary file followed by `os.replace`, so no partial target configuration is written. No dependency was added.

The documentation-manager agent now uses the controlled Evidence Status vocabulary from `AGENTS.md`: `PENDING`, `NOT_AVAILABLE`, `NOT_EXECUTED`, `INFERRED`, `OBSERVED`, and `VERIFIED`. `BLOCKED` is not an evidence status.

## Verification evidence

| Stage | Command | Result |
|---|---|---|
| RED | `python -m unittest tests.platform.test_config_rewrite -v` | Exit 1; 2 tests ran, 3 assertions failed. The prior global substitutions rewrote `other_mcp` values (including multiline `args`) and accepted missing/type-invalid targets. |
| GREEN | `python -m unittest tests.platform.test_config_rewrite -v` | Exit 0; 2 tests passed. |
| Existing configuration regression | `python -m unittest tests.platform.test_config_rewrite tests.platform.test_manifest_contract -v` | Exit 0; 9 tests passed. |
| TOML parse | `python -c "import tomllib; from pathlib import Path; tomllib.loads(Path('.codex/config.toml').read_text(encoding='utf-8')); print('config.toml: TOML parse OK')"` | Exit 0; `config.toml: TOML parse OK`. |
| Existing validator contract | `python -m unittest tests.platform.test_validator_contract -v` | Exit 1; 27 tests ran, 11 failed before their fixture assertions because the current environment reports `MCP_VERSION_UNSUPPORTED`. This task did not change dependencies or the validator. |

No installer or `pip install` command was run. The focused test uses a real temporary two-MCP config and invokes the script as a subprocess; it does not modify the repository's live configuration.

## Limits and follow-up

This is a local configuration rewrite verification, not a Codex restart or MCP service-start acceptance. It does not execute `scripts/setup.ps1`, install dependencies, or contact external services. Independent testing and review remain separate lifecycle activities.
