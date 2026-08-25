from __future__ import annotations

import argparse
import re
from pathlib import Path


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite company_context MCP launch paths as absolute paths derived from the repository root."
    )
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    config_path = root / ".codex" / "config.toml"
    text = config_path.read_text(encoding="utf-8")

    command = _toml_string(str(root / ".venv" / "Scripts" / "python.exe"))
    server = _toml_string(str(root / "tools" / "mcp" / "company-context" / "server.py"))
    cwd = _toml_string(str(root))

    text = re.sub(r'^\s*command\s*=.*$', lambda m: f'command = "{command}"', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*args\s*=.*$', lambda m: f'args = ["{server}"]', text, flags=re.MULTILINE)
    text = re.sub(r'^\s*cwd\s*=.*$', lambda m: f'cwd = "{cwd}"', text, flags=re.MULTILINE)

    config_path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Regenerated absolute launch paths for {root}")


if __name__ == "__main__":
    main()
