#!/usr/bin/env bash
set -euo pipefail

# Create a .venv using Python 3.10.5 (preferred).
# Usage examples:
#   ./scripts/setup_venv.sh                       # auto-detect
#   ./scripts/setup_venv.sh python3.10            # explicit interpreter
#   ./scripts/setup_venv.sh py -3.10              # Windows (py launcher)

expected_version="3.10.5"
venv_dir=".venv"

log() { printf "[%s] %s\n" "setup_venv" "$*"; }
fail() { printf "[ERROR] %s\n" "$*" >&2; exit 2; }

resolve_python() {
  # If user supplied a command, use it (supports multi-word like: py -3.10)
  if [ "$#" -gt 0 ]; then
    local cmd=("$@")
    if command -v "${cmd[0]}" >/dev/null 2>&1; then
      printf '%s\n' "${cmd[@]}"
      return 0
    else
      fail "Interpreter not found: ${cmd[0]}"
    fi
  fi

  # Try common candidates (single-word and multi-word)
  # Order: exact python3.10, python3, python, py -3.10
  local -a candidates_single=(python3.10 python3 python)
  local -a candidates_multi=("py -3.10")

  for c in "${candidates_single[@]}"; do
    if command -v "$c" >/dev/null 2>&1; then
      printf '%s\n' "$c"; return 0
    fi
  done

  for c in "${candidates_multi[@]}"; do
    # split into array
    IFS=' ' read -r -a parts <<<"$c"
    if command -v "${parts[0]}" >/dev/null 2>&1; then
      printf '%s\n' "$c"; return 0
    fi
  done

  return 1
}

python_cmd_str=$(resolve_python "$@" || true)
if [ -z "${python_cmd_str}" ]; then
  fail "No suitable Python found. Install Python ${expected_version} or pass an interpreter (e.g.,: ./scripts/setup_venv.sh py -3.10)"
fi

# Convert command string to array safely
IFS=' ' read -r -a PYTHON_CMD <<<"${python_cmd_str}"

log "Using python: ${PYTHON_CMD[*]}"

# Verify version
detected_version=$("${PYTHON_CMD[@]}" -c 'import platform; print(platform.python_version())' || true)
if [ -z "$detected_version" ]; then
  fail "Failed to invoke Python interpreter to read version."
fi

if [ "$detected_version" != "$expected_version" ]; then
  log "Detected Python version: $detected_version (expected $expected_version)"
  # Allow 3.10.x but warn if not exact patch
  case "$detected_version" in
    3.10.*) log "Proceeding with 3.10.x; if you specifically need $expected_version, ensure that version is installed and re-run." ;;
    *) fail "Python 3.10.x required. Found: $detected_version" ;;
  esac
fi

"${PYTHON_CMD[@]}" -m venv "$venv_dir"
log "Created virtualenv in $venv_dir"

log "To activate (bash): source $venv_dir/bin/activate"
log "Then upgrade pip and install dependencies if you have a requirements.txt file:"
printf "%s\n" \
  "  python -m pip install --upgrade pip" \
  "  [ -f requirements.txt ] && python -m pip install -r requirements.txt || echo 'No requirements.txt found.'"
