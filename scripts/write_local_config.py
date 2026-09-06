from __future__ import annotations

import argparse
import os
import tempfile
import tomllib
from pathlib import Path


def _toml_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _value_end(section: str, start: int) -> int:
    """Return the end of one TOML value without consuming its comment/newline."""
    depth = 0
    quote: str | None = None
    index = start
    while index < len(section):
        char = section[index]
        if quote:
            if char == "\\" and quote.startswith('"'):
                index += 2
                continue
            if section.startswith(quote, index):
                index += len(quote)
                # TOML permits one/two extra quote characters at a multiline end.
                if len(quote) == 3:
                    while index < len(section) and section[index] == quote[0]:
                        index += 1
                quote = None
                continue
            index += 1
            continue
        if char in ('"', "'"):
            quote = char * 3 if section.startswith(char * 3, index) else char
            index += len(quote)
            continue
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "#":
            if depth == 0:
                return index
            newline = section.find('\n', index)
            index = len(section) if newline < 0 else newline + 1
            continue
        elif char in "\r\n" and depth == 0:
            return index
        index += 1
    if quote or depth:
        raise ValueError("unterminated TOML launch value")
    return index


def _launch_spans(text: str) -> dict[str, tuple[int, int]]:
    """Walk real TOML statements, never lines embedded in string values."""
    index = 0
    in_target = False
    spans = {}
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        if text[index] == '#':
            newline = text.find('\n', index)
            index = len(text) if newline < 0 else newline + 1
            continue
        if text[index] == '[':
            newline = text.find('\n', index)
            end = len(text) if newline < 0 else newline
            header = text[index:end]
            probe = tomllib.loads(header + '\n__launch_probe__ = true\n')
            in_target = probe == {'mcp_servers': {'company_context': {'__launch_probe__': True}}}
            index = end
            continue
        key_start = index
        # Quoted keys may contain '='. Skip them before locating the delimiter.
        quote = None
        while index < len(text):
            char = text[index]
            if quote:
                if char == '\\' and quote == '"':
                    index += 2
                    continue
                if char == quote:
                    quote = None
            elif char in ('"', "'"):
                quote = char
            elif char == '=':
                break
            index += 1
        key_text = text[key_start:index].strip()
        index += 1
        while index < len(text) and text[index] in ' \t':
            index += 1
        value_start = index
        end = _value_end(text, index)
        value_end = end
        while value_end > value_start and text[value_end - 1] in ' \t':
            value_end -= 1
        if in_target:
            parsed_key = tomllib.loads(key_text + ' = 0')
            for key in ('command', 'args', 'cwd'):
                if parsed_key == {key: 0}:
                    if key in spans:
                        raise ValueError(f'duplicate launch key {key}')
                    spans[key] = (value_start, value_end)
        index = end
    if set(spans) != {'command', 'args', 'cwd'}:
        raise ValueError('company_context launch values could not be located safely')
    return spans


def rewrite_company_context(text: str, root: Path) -> str:
    """Rewrite only company_context launch values after validating the TOML input."""
    try:
        parsed = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"config is not valid TOML: {error}") from error

    target = parsed.get("mcp_servers", {}).get("company_context")
    if not isinstance(target, dict):
        raise ValueError("config is missing [mcp_servers.company_context]")
    if not isinstance(target.get("command"), str):
        raise ValueError("company_context command must be a string")
    if not isinstance(target.get("args"), list) or not all(isinstance(item, str) for item in target["args"]):
        raise ValueError("company_context args must be a string list")
    if not isinstance(target.get("cwd"), str):
        raise ValueError("company_context cwd must be a string")

    spans = _launch_spans(text)
    command = _toml_string(str(root / ".venv" / "Scripts" / "python.exe"))
    server = _toml_string(str(root / "tools" / "mcp" / "company-context" / "server.py"))
    cwd = _toml_string(str(root))
    replacements = dict((
        ("command", f'"{command}"'),
        ("args", f'["{server}"]'),
        ("cwd", f'"{cwd}"'),
    ))
    rewritten = text
    for key, (start, end) in sorted(spans.items(), key=lambda item: item[1][0], reverse=True):
        rewritten = rewritten[:start] + replacements[key] + rewritten[end:]
    try:
        actual = tomllib.loads(rewritten)
    except tomllib.TOMLDecodeError as error:
        raise ValueError(f"rewritten config is not valid TOML: {error}") from error
    expected = {'command': str(root / '.venv' / 'Scripts' / 'python.exe'),
                'args': [str(root / 'tools' / 'mcp' / 'company-context' / 'server.py')],
                'cwd': str(root)}
    target.update(expected)
    if actual != parsed:
        raise ValueError('rewritten config does not match the exact intended launch change')
    return rewritten


def _atomic_write(path: Path, data: bytes) -> None:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as temporary:
            temporary.write(data)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rewrite company_context MCP launch paths as absolute paths derived from the repository root."
    )
    parser.add_argument("root", nargs="?", default=".")
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    config_path = root / ".codex" / "config.toml"
    original = config_path.read_bytes()
    try:
        rewritten = rewrite_company_context(original.decode("utf-8"), root)
    except (UnicodeDecodeError, ValueError) as error:
        parser.error(str(error))
    _atomic_write(config_path, rewritten.encode("utf-8"))
    print(f"Regenerated absolute company_context launch paths for {root}")


if __name__ == "__main__":
    main()
