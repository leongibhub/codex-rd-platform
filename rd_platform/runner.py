"""Bounded local process adapter for trusted CLI callers, never an HTTP tool."""
from __future__ import annotations

import math
import os
from pathlib import Path
import re
import subprocess
import threading
import time

from rd_platform._process_tree import ProcessTree


def _secret_values(argv, explicit):
    values = {value for key, value in os.environ.items()
              if re.search(r'TOKEN|SECRET|PASSWORD|API[_-]?KEY', key, re.I) and value}
    values.update(value for value in explicit if value)
    for index, arg in enumerate(argv):
        key, separator, value = arg.partition('=')
        if key.startswith('-') and re.search(r'TOKEN|SECRET|PASSWORD|API[_-]?KEY', key, re.I):
            if separator and value:
                values.add(value)
            elif index + 1 < len(argv) and argv[index + 1]:
                values.add(argv[index + 1])
    return sorted(values, key=len, reverse=True)


class _BoundedRedactor:
    """Retain capped evidence and an undecidable secret-prefix overlap."""
    def __init__(self, values, cap):
        self.secrets = [value.encode('utf-8') for value in values]
        self.cap = cap
        self.pending = b''
        self.output = bytearray()

    def feed(self, chunk, final=False):
        data = self.pending + chunk
        index = 0
        while index < len(data):
            remaining = data[index:]
            match = next((secret for secret in self.secrets if remaining.startswith(secret)), None)
            partial = any(secret.startswith(remaining) for secret in self.secrets)
            if partial and not final:
                break
            if match or partial:
                token = b'[REDACTED]'
                index += len(match) if match else len(remaining)
            else:
                token = data[index:index + 1]
                index += 1
            self.output.extend(token[:max(0, self.cap - len(self.output))])
        self.pending = data[index:]

    def text(self):
        self.feed(b'', final=True)
        return bytes(self.output).decode('utf-8', 'replace').encode('utf-8')[:self.cap].decode('utf-8', 'ignore')


def run_command(argv: list[str], cwd: str | Path, *, timeout: float = 60,
                max_output_bytes: int = 65536, explicit_secret_values=()) -> dict:
    """Execute an owned local process tree with bounded in-memory evidence."""
    if not isinstance(argv, list) or not argv or not all(
        isinstance(arg, str) and '\0' not in arg for arg in argv
    ) or not argv[0].strip():
        raise ValueError('argv must be a nonempty list of strings')
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 0 < timeout <= 86400:
        raise ValueError('timeout must be finite and between 0 and 86400 seconds')
    if isinstance(max_output_bytes, bool) or not isinstance(max_output_bytes, int) or not 1 <= max_output_bytes <= 10_000_000:
        raise ValueError('max_output_bytes must be between 1 and 10000000')
    if isinstance(explicit_secret_values, str) or not isinstance(explicit_secret_values, (list, tuple, set)) or not all(isinstance(value, str) for value in explicit_secret_values):
        raise ValueError('explicit_secret_values must be a collection of strings')
    workdir = Path(cwd).resolve(strict=True)
    if not workdir.is_dir():
        raise ValueError('cwd must be a directory')
    secrets = _secret_values(argv, explicit_secret_values)

    def redact(text):
        for secret in secrets:
            text = text.replace(secret, '[REDACTED]')
        return text

    started = time.monotonic()
    timed_out = False
    launch_error = None
    exit_code = None
    exceeded = threading.Event()
    reader_failed = threading.Event()
    evidence = _BoundedRedactor(secrets, max_output_bytes)
    tree = None
    reader = None
    failures = []

    def attempt(label, operation, fallback=None):
        try:
            return operation()
        except (OSError, subprocess.SubprocessError) as error:
            # Error text may contain argv/secrets. Record only fixed context/type.
            failures.append(f'{label}: {type(error).__name__}')
            return fallback

    def drain():
        count = 0
        try:
            while chunk := tree.process.stdout.read(4096):
                remaining = max(0, max_output_bytes - count)
                count += len(chunk)
                if count > max_output_bytes:
                    exceeded.set()
                evidence.feed(chunk[:remaining])
        except OSError:
            reader_failed.set()

    try:
        tree = ProcessTree(argv, workdir)
        reader = threading.Thread(target=drain, daemon=True)
        reader.start()
        while tree.active():
            timed_out = time.monotonic() - started >= timeout
            if timed_out or exceeded.is_set() or reader_failed.is_set():
                tree.stop()
                break
            exceeded.wait(min(0.01, max(0.001, timeout - (time.monotonic() - started))))
        tree.process.wait(timeout=5)
        exit_code = tree.process.returncode
    except (OSError, subprocess.SubprocessError) as error:
        failures.append(f'Execution or containment failed: {type(error).__name__}')
    finally:
        if tree:
            # Unknown liveness must be treated as active. Each cleanup is attempted
            # independently so a query/terminate error cannot suppress Job closure.
            if attempt('Containment query failed', tree.active, True):
                attempt('Termination failed', tree.stop)
            close_failed = object()
            if attempt('Containment close failed', tree.close, close_failed) is close_failed:
                attempt('Termination retry failed', tree.stop)
                attempt('Containment close retry failed', tree.close)
            attempt('Process wait failed', lambda: tree.process.wait(timeout=5))
            if reader:
                reader.join(timeout=5)
                if reader.is_alive():
                    reader_failed.set()
            attempt('Output close failed', tree.process.stdout.close)
    if reader_failed.is_set():
        failures.append('Output collection failed')
    if failures:
        launch_error = '; '.join(failures)
    timed_out = timed_out or time.monotonic() - started >= timeout
    truncated = exceeded.is_set()
    return {
        'argv': [redact(arg) for arg in argv], 'cwd': redact(str(workdir)),
        'exit_code': exit_code, 'stdout': evidence.text(),
        'duration_seconds': round(time.monotonic() - started, 6),
        'timed_out': timed_out, 'output_truncated': truncated,
        'launch_error': redact(launch_error) if launch_error else None,
        'status': 'PASS' if exit_code == 0 and not timed_out and not truncated and not launch_error else 'FAIL',
    }
