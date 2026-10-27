#!/usr/bin/env bash
set -Eeuo pipefail
source_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/scripts"
cp "$source_root/scripts/check-local.sh" "$work/scripts/check-local.sh"

# A controlled fake interpreter avoids network package installs while exercising
# the actual validation entrypoint and its environment selection.
cat > "$work/fake-python" <<'PYTHON'
#!/usr/bin/env bash
set -Eeuo pipefail
if [[ "$1" == "-c" ]]; then
    printf '%s\n' "$STUB_ID"
elif [[ "$1" == "-m" && "$2" == "venv" ]]; then
    mkdir -p "$3/bin"
    printf '%s\n' "$STUB_ID" > "$3/.identity"
    cat > "$3/bin/python" <<'VENV'
#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [[ "$1" == "-c" ]]; then
    cat "$root/.identity"
elif [[ "$1" == "-m" ]]; then
    printf '%s\n' "$2" >> "$root/.actions"
else
    exit 77
fi
VENV
    chmod +x "$3/bin/python"
else
    exit 77
fi
PYTHON
chmod +x "$work/fake-python"

STUB_ID='python-3.11' PYTHON="$work/fake-python" bash "$work/scripts/check-local.sh" >/dev/null
[[ "$(cat "$work/.venv/.identity")" == 'python-3.11' ]]
[[ "$(wc -l < "$work/.venv/.actions")" -eq 3 ]]
if STUB_ID='python-3.12' PYTHON="$work/fake-python" bash "$work/scripts/check-local.sh" >"$work/error.log" 2>&1; then
    echo 'ERROR: reused an environment from a different interpreter' >&2
    exit 1
fi
grep -q 'Refusing to run checks' "$work/error.log"
[[ "$(wc -l < "$work/.venv/.actions")" -eq 3 ]]

STUB_ID='python-3.12' PYTHON="$work/fake-python" VENV='.venv-py312' bash "$work/scripts/check-local.sh" >/dev/null
[[ "$(cat "$work/.venv-py312/.identity")" == 'python-3.12' ]]
[[ "$(wc -l < "$work/.venv-py312/.actions")" -eq 3 ]]
STUB_ID='python-3.11' PYTHON="$work/fake-python" bash "$work/scripts/check-local.sh" >/dev/null
[[ "$(wc -l < "$work/.venv/.actions")" -eq 6 ]]
printf 'PASS: interpreter mismatch blocked, separate VENV accepted, original VENV reusable\n'
