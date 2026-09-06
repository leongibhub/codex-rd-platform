#!/usr/bin/env python3
"""Portable manifest-v1 build and validation adapter for C++17 toolchains."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys


APP = Path(__file__).resolve().parent
ROOT = APP.parents[2]
BUILD = ROOT / ".rd-platform" / "build" / "cpp_inventory"


def wsl_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if not drive:
        raise RuntimeError("the WSL adapter requires a drive-letter workspace path")
    return "/mnt/" + drive + resolved.as_posix()[2:]


def use_wsl() -> bool:
    """Keep existing Windows WSL support when no native GNU C++ is available."""
    return os.name == "nt" and shutil.which("g++") is None


def tool_path(path: Path) -> str:
    return wsl_path(path) if use_wsl() else str(path)


def invoke(arguments: list[str]) -> None:
    command = ["wsl.exe", "--cd", wsl_path(APP), "--", *arguments] if use_wsl() else arguments
    completed = subprocess.run(command, cwd=None if use_wsl() else APP, check=False)
    if completed.returncode:
        raise RuntimeError(f"WSL command failed with exit {completed.returncode}")


def compile_application() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    executable = BUILD / ("inventory.exe" if os.name == "nt" and not use_wsl() else "inventory")
    invoke(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "inventory.cpp", "main.cpp", "-o", tool_path(executable)])
    return executable


def compile_unit_tests() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    executable = BUILD / ("test_inventory.exe" if os.name == "nt" and not use_wsl() else "test_inventory")
    invoke(["g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "inventory.cpp", "test_inventory.cpp", "-o", tool_path(executable)])
    return executable


def run_program(executable: Path, *arguments: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    command = ["wsl.exe", "--", wsl_path(executable), *arguments] if use_wsl() else [str(executable), *arguments]
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != expect:
        raise RuntimeError(f"inventory returned {completed.returncode}, expected {expect}: {completed.stderr.strip()}")
    return completed


def integration() -> None:
    executable = compile_application()
    data = BUILD / "integration.tsv"
    if data.exists():
        data.unlink()
    run_program(executable, tool_path(data), "add", "widget", "7")
    queried = run_program(executable, tool_path(data), "get", "widget")
    if queried.stdout != "7\n":
        raise RuntimeError("TC-CPP-004: separate process did not reload committed stock")
    before = data.read_bytes()
    run_program(executable, tool_path(data), "deduct", "widget", "8", expect=1)
    if data.read_bytes() != before:
        raise RuntimeError("TC-CPP-002: insufficient deduction modified persisted data")
    listed = run_program(executable, tool_path(data), "list")
    if listed.stdout != "widget\t7\n":
        raise RuntimeError("TC-CPP-003: list result was unexpected")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("build", "unit", "integration"), required=True)
    phase = parser.parse_args().phase
    try:
        if phase == "build":
            compile_application()
        elif phase == "unit":
            executable = compile_unit_tests()
            result = run_program(executable, tool_path(BUILD / "unit"))
            print(result.stdout, end="")
        else:
            integration()
            print("3 integration checks passed")
        return 0
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
