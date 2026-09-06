#!/usr/bin/env bash
# Native Linux setup for TASK-V3-019.  All mutable paths remain in this checkout.
set -euo pipefail

python_command="python3"
skip_dependency_install=false

usage() {
  cat <<'EOF'
Usage: ./scripts/setup.sh [--python-command COMMAND] [--skip-dependency-install]

Creates or reuses this checkout's .venv, installs the constrained MCP
dependencies, regenerates the local MCP launch configuration, and runs the
real platform/MCP health check.  It never changes global Git or Python state.
EOF
}

fail() {
  printf '%s\n' "$1" >&2
  exit 1
}

run_native() {
  local description="$1"
  shift
  "$@" || {
    local status=$?
    fail "$description failed with exit code $status"
  }
}

while (($#)); do
  case "$1" in
    --python-command)
      (($# >= 2)) || fail "--python-command requires a command."
      python_command="$2"
      shift 2
      ;;
    --skip-dependency-install)
      skip_dependency_install=true
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown option: $1"
      ;;
  esac
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
root=$(cd -- "$script_dir/.." && pwd -P)
venv_python="$root/.venv/bin/python"
knowledge_local="$root/knowledge/local"

cd -- "$root"
printf '%s\n' '=== Codex R&D Platform Linux Setup ==='
printf 'Root: %s\n' "$root"

command -v git >/dev/null 2>&1 || fail "Git is not installed or not in PATH."
run_native "Git availability check" git --version
[[ $(git rev-parse --is-inside-work-tree 2>/dev/null) == "true" ]] || fail "The setup directory must be an existing Git work tree."
run_native "Git status check" git status --porcelain

git_user_name=$(git config --get user.name 2>/dev/null || true)
[[ -n "$git_user_name" ]] || fail "Git user.name must be configured before setup."
git_user_email=$(git config --get user.email 2>/dev/null || true)
[[ -n "$git_user_email" ]] || fail "Git user.email must be configured before setup."

command -v "$python_command" >/dev/null 2>&1 || fail "Python is not installed or '$python_command' is not in PATH."
"$python_command" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
  || fail "Python version must be 3.11 or newer."

if [[ ! -x "$venv_python" ]]; then
  run_native "Python virtual environment creation" "$python_command" -m venv --copies "$root/.venv"
fi
[[ -x "$venv_python" ]] || fail "Python virtual environment executable was not created."
resolved_root=$(readlink -f -- "$root") || fail "Repository root could not be resolved."
resolved_venv_root=$(readlink -f -- "$root/.venv") || fail "Existing virtual environment must resolve inside this repository."
resolved_venv_python=$(readlink -f -- "$venv_python") || fail "Existing virtual environment interpreter must resolve inside this repository."
[[ "$resolved_venv_root" == "$resolved_root/.venv" || "$resolved_venv_root" == "$resolved_root/.venv/"* ]] \
  || fail "Existing virtual environment must resolve inside this repository."
[[ "$resolved_venv_python" == "$resolved_venv_root" || "$resolved_venv_python" == "$resolved_venv_root/"* ]] \
  || fail "Existing virtual environment interpreter must resolve inside this repository."
"$venv_python" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' \
  || fail "Repository virtual environment Python version must be 3.11 or newer."

if [[ "$skip_dependency_install" == false ]]; then
  run_native "Constrained dependency installation" "$venv_python" -m pip install -r "$root/tools/mcp/company-context/requirements.txt"
fi
run_native "Dependency consistency check" "$venv_python" -m pip check

mkdir -p -- "$knowledge_local"
[[ -d "$knowledge_local" ]] || fail "Local knowledge directory was not created."
export COMPANY_LOCAL_ROOTS="${COMPANY_LOCAL_ROOTS:-$knowledge_local}"

run_native "Absolute local MCP path generation" "$venv_python" "scripts/write_local_config.py" "$root"
run_native "Platform validation" "$venv_python" "scripts/validate_platform.py"

printf '\nSetup complete.\n'
printf '%s\n' 'Next: configure optional service environment variables, then start Codex from this repository.'
