"""Command-line entry point for the local V2 runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def default_db_path() -> Path:
    return Path.cwd() / ".rd-platform" / "state.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="rd_platform", description="本地研发运行台")
    parser.add_argument("--db", type=Path, default=default_db_path(), help="SQLite 状态库路径")
    commands = parser.add_subparsers(dest="operation", required=True)

    serve = commands.add_parser("serve", help="启动本地看板")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8020)

    command = commands.add_parser("command", help="执行受控 Runtime 命令")
    command.add_argument("name")
    command.add_argument("data", help="JSON object")
    command.add_argument("--request-id")

    snapshot = commands.add_parser("snapshot", help="输出运行快照 JSON")
    snapshot.add_argument("--project-id")

    discover = commands.add_parser("discover", help="生成待确认的需求发现模型")
    discover.add_argument("idea")

    freeze = commands.add_parser("freeze", help="根据确认答案生成草案 SRS/RTM")
    freeze.add_argument("model", help="discover 输出的 JSON object")
    freeze.add_argument("answers", help="确认答案的 JSON object")

    report = commands.add_parser("report", help="从真实快照生成报告 JSON")
    report.add_argument("--project-id")

    run = commands.add_parser("run", help="由可信 CLI 执行命令并记录运行证据")
    run.add_argument("--task-id", required=True)
    run.add_argument("--agent-id", required=True)
    run.add_argument("--phase", required=True, choices=("implementation", "unit", "integration", "review"))
    run.add_argument("--cwd", type=Path, default=Path.cwd())
    run.add_argument("--timeout", type=float, default=60)
    run.add_argument("argv", nargs=argparse.REMAINDER, help="以 -- 分隔的 argv；不会使用 shell")
    return parser


def _object(value: str, label: str) -> dict[str, Any]:
    try:
        parsed = json.loads(value, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(f"non-finite JSON number is not allowed: {token}")))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be valid JSON: {exc.msg}") from exc
    except (ValueError, RecursionError) as exc:
        raise ValueError(f"{label} must be valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    return parsed


def main(argv: list[str] | None = None) -> int:
    # Subprocess callers consume this CLI as a JSON interface.  Windows
    # console code pages must not change the bytes of that interface.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.operation == "serve":
            from .web import create_server
            args.db.parent.mkdir(parents=True, exist_ok=True)
            server = create_server(args.db, host=args.host, port=args.port)
            print(f"本地运行台：http://127.0.0.1:{server.server_port}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                server.server_close()
            return 0

        # Discovery is a pure, no-model helper.  Do not create an unrelated
        # runtime database merely to turn an idea or answers into a draft.
        if args.operation == "discover":
            from .discovery import discover
            print(json.dumps(discover(args.idea), ensure_ascii=False, allow_nan=False, indent=2))
            return 0
        if args.operation == "freeze":
            from .discovery import freeze
            print(json.dumps(freeze(_object(args.model, "model"), _object(args.answers, "answers")), ensure_ascii=False, allow_nan=False, indent=2))
            return 0

        from .runtime import Runtime
        runtime = Runtime(args.db)
        exit_code = 0
        if args.operation == "command":
            result = runtime.execute(args.name, _object(args.data, "data"), request_id=args.request_id)
        elif args.operation == "snapshot":
            result = runtime.snapshot(args.project_id)
        elif args.operation == "discover":
            from .discovery import discover
            result = discover(args.idea)
        elif args.operation == "freeze":
            from .discovery import freeze
            result = freeze(_object(args.model, "model"), _object(args.answers, "answers"))
        elif args.operation == "run":
            command_argv = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            if not command_argv:
                raise ValueError("run requires argv after --")
            from .runner import run_command
            started = runtime.execute("run.start", {"task_id": args.task_id, "agent_id": args.agent_id, "phase": args.phase})
            interrupted: BaseException | None = None
            try:
                execution = run_command(command_argv, args.cwd, timeout=args.timeout)
            except BaseException as exc:  # Runtime state must not retain an ACTIVE run on adapter failure.
                interrupted = exc
                execution = {
                    "argv": ["[NOT_RECORDED_AFTER_RUNNER_FAILURE]"], "cwd": str(args.cwd), "exit_code": None, "stdout": "",
                    "duration_seconds": 0, "timed_out": False, "output_truncated": False,
                    "launch_error": f"{type(exc).__name__}: runner invocation failed", "status": "FAIL",
                }
            status = execution["status"]
            try:
                finished = runtime.execute("run.finish", {
                    "run_id": started["id"], "status": status,
                    "summary": "trusted CLI command completed" if status == "PASS" else "trusted CLI command failed",
                    "evidence": execution,
                })
            except ValueError as exc:
                raise ValueError("run was cancelled or invalidated before evidence could be recorded") from exc
            if interrupted is not None:
                raise interrupted
            result = {"task": finished, "execution": execution}
            exit_code = 0 if status == "PASS" else 1
        else:
            from .reporting import report
            result = report(runtime.snapshot(args.project_id))
    except (KeyError, ValueError, OSError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
    return exit_code
