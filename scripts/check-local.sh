#!/usr/bin/env bash
set -Eeuo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
PYTHON="${PYTHON:-python3}"
VENV="${VENV:-.venv}"

# sys._base_executable identifies the interpreter beneath a virtualenv, so
# PYTHON may itself name a venv interpreter without producing a false mismatch.
identity_code='import os, sys; print(os.path.realpath(getattr(sys, "_base_executable", sys.executable)) + "|" + sys.implementation.name + "|" + str(sys.version_info.major) + "." + str(sys.version_info.minor))'
selected_identity="$("$PYTHON" -c "$identity_code")"

if [[ ! -x "$VENV/bin/python" ]]; then
    "$PYTHON" -m venv "$VENV"
fi
actual_identity="$("$VENV/bin/python" -c "$identity_code")"
if [[ "$actual_identity" != "$selected_identity" ]]; then
    printf 'Refusing to run checks: %s uses %s, but PYTHON=%s selects %s.\n' \
        "$VENV" "$actual_identity" "$PYTHON" "$selected_identity" >&2
    printf 'Use a separate VENV path for each interpreter, e.g. VENV=.venv-py312 PYTHON=python3.12.\n' >&2
    exit 2
fi

"$VENV/bin/python" -m pip install -e '.[dev]'
"$VENV/bin/python" -m ruff check .
"$VENV/bin/python" -m pytest
echo "Cura QIDI local checks passed"
