"""Build the existing Java 8 application into a confined, initially empty tree."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


APP = Path(__file__).resolve().parent
ROOT = APP.parents[2]
SOURCES = ("Booking.java", "BookingException.java", "BookingStore.java",
           "BookingCli.java", "BookingStoreTest.java", "BookingCliProcessTest.java")


def reject_link(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("build output contains a symlink")
    if os.path.lexists(path):
        attributes = getattr(path.stat(follow_symlinks=False), "st_file_attributes", 0)
        if attributes & 0x400:
            raise ValueError("build output contains a junction or reparse point")


def classes_directory(build: Path) -> Path:
    """Validate before creating output; this is not a concurrent-process sandbox."""
    base = ROOT / ".rd-platform" / "build"
    if not build.is_absolute() or ".." in build.parts:
        raise ValueError("build path must be absolute and contain no parent traversal")
    try:
        relative = build.relative_to(base)
    except ValueError as error:
        raise ValueError("build path must remain under repository .rd-platform/build") from error
    if not relative.parts:
        raise ValueError("build path must name an application directory, not the build base")
    classes = build / "classes"
    current = ROOT
    for component in classes.relative_to(ROOT).parts:
        current = current / component
        reject_link(current)
    classes.resolve().relative_to(base.resolve())
    if classes.exists():
        for directory, directories, files in os.walk(classes, followlinks=False):
            for name in directories + files:
                reject_link(Path(directory) / name)
    return classes


def compile_application(javac: str, build: Path) -> int:
    classes = classes_directory(Path(build))
    if not Path(javac).is_absolute() or not Path(javac).is_file():
        raise ValueError("javac must identify an available absolute compiler path")
    classes.mkdir(parents=True, exist_ok=True)
    argv = [javac, "-encoding", "UTF-8", "-d", str(classes)]
    argv.extend(str(APP / "src" / "booking" / name) for name in SOURCES)
    completed = subprocess.run(argv, cwd=APP, shell=False, check=False, timeout=120)
    return completed.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--javac", required=True)
    parser.add_argument("--build", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        return compile_application(args.javac, args.build)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print("Java build failed: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
