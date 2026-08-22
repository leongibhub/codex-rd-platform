from pathlib import Path
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]

required = [
    "AGENTS.md",
    ".codex/config.toml",
    ".codex/agents/researcher.toml",
    ".codex/agents/product-manager.toml",
    ".codex/agents/requirement-analyst.toml",
    ".codex/agents/architect.toml",
    ".codex/agents/developer.toml",
    ".codex/agents/tester.toml",
    ".codex/agents/reviewer.toml",
    ".codex/agents/documentation-manager.toml",
    ".codex/agents/release-manager.toml",
    "docs/03-requirements/requirement-traceability-matrix.md",
    "tools/mcp/company-context/server.py",
]

errors = []
for rel in required:
    if not (ROOT / rel).exists():
        errors.append(f"MISSING: {rel}")

for p in (ROOT / ".codex/agents").glob("*.toml"):
    try:
        data = tomllib.loads(p.read_text(encoding="utf-8"))
        for key in ("name", "description", "developer_instructions"):
            if not data.get(key):
                errors.append(f"{p.relative_to(ROOT)} missing {key}")
    except Exception as e:
        errors.append(f"{p.relative_to(ROOT)} invalid TOML: {e}")

try:
    tomllib.loads((ROOT / ".codex/config.toml").read_text(encoding="utf-8"))
except Exception as e:
    errors.append(f".codex/config.toml invalid TOML: {e}")

skill_files = list((ROOT / ".agents/skills").glob("*/SKILL.md"))
if len(skill_files) < 10:
    errors.append(f"Only {len(skill_files)} skills found")

if errors:
    print("PLATFORM VALIDATION: FAIL")
    for e in errors:
        print(" -", e)
    sys.exit(1)

print("PLATFORM VALIDATION: PASS")
print(f"Agents: {len(list((ROOT / '.codex/agents').glob('*.toml')))}")
print(f"Skills: {len(skill_files)}")
print(f"Docs/Templates: {len(list((ROOT / 'docs').rglob('*.md')))}")
