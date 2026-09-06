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

    bootstrap = commands.add_parser("orchestrate-start", help="由粗略想法创建可恢复的研发工作流，不伪造批准")
    bootstrap.add_argument("--idea", required=True)
    bootstrap.add_argument("--name", required=True)
    bootstrap.add_argument("--repository-root", type=Path, required=True)
    bootstrap.add_argument("--request-id", required=True)
    service = commands.add_parser("worker-service", help="运行真实后台工作单执行器")
    service.add_argument("--config", type=Path, required=True)
    service.add_argument("--once", action="store_true")
    deploy = commands.add_parser("deploy-run", help="执行显式部署/健康/回滚清单")
    deploy.add_argument("--config", type=Path, required=True)
    deploy.add_argument("--action", choices=("deploy", "rollback"), default="deploy")
    for operation in ("approval-challenge", "approval-register"):
        approval = commands.add_parser(operation, help="生成待签挑战或验证外部签名审批")
        approval.add_argument("--provider-config", type=Path, required=True)
        approval.add_argument("--request", type=Path, required=True)
        approval.add_argument("--operator", required=True)
        approval.add_argument("--challenge", type=Path, required=True)
        if operation == "approval-register":
            approval.add_argument("--signature", type=Path, required=True)

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

    lifecycle = commands.add_parser("lifecycle", help="读取版本化生命周期、Gate、追踪与测试事实")
    lifecycle.add_argument("--project-id", required=True)
    lifecycle.add_argument("--after-sequence", type=int, default=0)
    lifecycle.add_argument("--limit", type=int, default=200)
    lifecycle_collection = commands.add_parser("lifecycle-collection", help="分页读取一个公开生命周期集合")
    lifecycle_collection.add_argument("--project-id", required=True)
    lifecycle_collection.add_argument("collection")
    lifecycle_collection.add_argument("--after-cursor")
    lifecycle_collection.add_argument("--limit", type=int, default=200)
    lifecycle_report = commands.add_parser("lifecycle-report", help="生成当前版本正式测试报告；不改变Gate")
    lifecycle_report.add_argument("--project-id", required=True)
    project_export = commands.add_parser("project-export", help="导出独立活动项目文档；拒绝覆盖")
    project_export.add_argument("--project-id", required=True)
    project_export.add_argument("--output-dir", type=Path, required=True)
    test_run = commands.add_parser("test-run", help="执行已基线化Case中的argv并登记V3真实结果")
    test_run.add_argument("--project-id", required=True)
    test_run.add_argument("--case-id", required=True)
    test_run.add_argument("--case-version", required=True, type=int)
    test_run.add_argument("--executor-id", required=True)
    test_run.add_argument("--timeout", type=float, default=60)
    commands.add_parser("stack-probe", help="只读探测本机技术栈工具")
    for operation, description in (("stack-run", "执行可信本地应用manifest的构建/测试"),
                                   ("stack-package", "生成带摘要的本地应用交付包")):
        stack = commands.add_parser(operation, help=description)
        stack.add_argument("manifest", type=Path)
        stack.add_argument("--root", type=Path, default=Path.cwd())
        if operation == "stack-run":
            stack.add_argument("--phase", action="append", choices=("build", "unit", "integration"))

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


def _config_file(path: Path) -> dict:
    with path.open('rb') as stream:
        raw = stream.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise ValueError('configuration exceeds 1 MiB budget')
    return _object(raw.decode('utf-8-sig'), 'configuration')


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

        if args.operation in {"stack-probe", "stack-run", "stack-package"}:
            from .stack_harness import probe_tools, run_matrix, package_app
            if args.operation == "stack-probe":
                result = probe_tools()
            elif args.operation == "stack-run":
                result = run_matrix(args.manifest, root=args.root, phases=args.phase)
            else:
                result = package_app(args.manifest, root=args.root)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
            return 0 if args.operation == "stack-probe" or result.get("status") == "PASS" else 1

        from .runtime import Runtime
        runtime = Runtime(args.db)
        exit_code = 0
        if args.operation in {"approval-challenge", "approval-register"}:
            from .approval_provider import SshApprovalProvider, create_approval_challenge, register_signed_approval
            from .store import Store
            provider = SshApprovalProvider(_config_file(args.provider_config))
            runtime = Runtime(args.db, approval_provider=provider)
            request = _config_file(args.request)
            if args.operation == "approval-challenge":
                challenge = create_approval_challenge(runtime, request, operator=args.operator, provider=provider)
                with args.challenge.open('xb') as output:
                    output.write(Store.dumps(challenge).encode('utf-8'))
                result = {'status': 'WAITING_FOR_SIGNATURE', 'challenge': str(args.challenge.resolve()),
                          'expires_at': challenge['expires_at'], 'approval_recorded': False}
            else:
                result = register_signed_approval(runtime, request, operator=args.operator, provider=provider,
                    response={'challenge': _config_file(args.challenge), 'signature_path': str(args.signature.resolve())})
        elif args.operation == "orchestrate-start":
            from .orchestration import start_project
            result = start_project(runtime, name=args.name, idea=args.idea,
                repository_root=args.repository_root, request_id=args.request_id)
        elif args.operation == "worker-service":
            from .worker_service import run_service
            result = run_service(runtime, _config_file(args.config), once=args.once)
            exit_code = 1 if result.get('status') == 'FAIL' else 0
        elif args.operation == "deploy-run":
            from .deployment import execute_deployment
            result = execute_deployment(runtime, _config_file(args.config), action=args.action)
            exit_code = 0 if result.get('status') in {'PASS', 'TRIAL_SUCCEEDED', 'TRIAL_ROLLED_BACK'} and not result.get('formal_registration_error') else 1
        elif args.operation == "command":
            result = runtime.execute(args.name, _object(args.data, "data"), request_id=args.request_id)
        elif args.operation == "snapshot":
            result = runtime.snapshot(args.project_id)
        elif args.operation == "lifecycle":
            result = runtime.lifecycle_snapshot(args.project_id, after_sequence=args.after_sequence, limit=args.limit)
        elif args.operation == "lifecycle-collection":
            result = runtime.lifecycle_collection(args.project_id, args.collection, limit=args.limit, after_cursor=args.after_cursor)
        elif args.operation == "lifecycle-report":
            from .lifecycle_reporting import lifecycle_report_from_runtime
            result = lifecycle_report_from_runtime(runtime, args.project_id)
        elif args.operation == "project-export":
            from .lifecycle_export import export_project
            result = export_project(runtime, args.project_id, args.output_dir)
        elif args.operation == "test-run":
            from .lifecycle_runner import run_case
            result = run_case(runtime, project_id=args.project_id, case_id=args.case_id,
                case_version=args.case_version, executor_id=args.executor_id, timeout=args.timeout)
            exit_code = 0 if result['execution']['result'] == 'PASS' else 1
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
