#!/usr/bin/env python3
"""Portable manifest-v1 build and validation adapter for the WSL C++ toolchain."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
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


def invoke(arguments: list[str]) -> None:
    command = ["wsl.exe", "--cd", wsl_path(APP), "--", *arguments]
    completed = subprocess.run(command, check=False)
    if completed.returncode:
        raise RuntimeError(f"WSL command failed with exit {completed.returncode}")


def compile_application() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    executable = BUILD / "inventory"
    invoke(["/usr/bin/g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "inventory.cpp", "main.cpp", "-o", wsl_path(executable)])
    return executable


def compile_unit_tests() -> Path:
    BUILD.mkdir(parents=True, exist_ok=True)
    executable = BUILD / "test_inventory"
    invoke(["/usr/bin/g++", "-std=c++17", "-Wall", "-Wextra", "-Werror", "inventory.cpp", "test_inventory.cpp", "-o", wsl_path(executable)])
    return executable


def run_program(executable: Path, *arguments: str, expect: int = 0) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["wsl.exe", "--", wsl_path(executable), *arguments], text=True, capture_output=True, check=False)
    if completed.returncode != expect:
        raise RuntimeError(f"inventory returned {completed.returncode}, expected {expect}: {completed.stderr.strip()}")
    return completed


def integration() -> None:
    executable = compile_application()
    data = BUILD / "integration.tsv"
    if data.exists():
        data.unlink()
    run_program(executable, wsl_path(data), "add", "widget", "7")
    queried = run_program(executable, wsl_path(data), "get", "widget")
    if queried.stdout != "7\n":
        raise RuntimeError("TC-CPP-004: separate process did not reload committed stock")
    before = data.read_bytes()
    run_program(executable, wsl_path(data), "deduct", "widget", "8", expect=1)
    if data.read_bytes() != before:
        raise RuntimeError("TC-CPP-002: insufficient deduction modified persisted data")
    listed = run_program(executable, wsl_path(data), "list")
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
            result = run_program(executable, wsl_path(BUILD / "unit"))
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
