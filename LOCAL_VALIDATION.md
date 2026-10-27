# Local validation

Run `bash scripts/check-local.sh`. It installs editable development dependencies,
runs Ruff, and runs pytest using the selected Python environment.

Former CI covered Python 3.10, 3.11, 3.12, and 3.13. Exercise each installed
interpreter using a separate environment directory:

```bash
PYTHON=python3.10 VENV=.venv-py310 bash scripts/check-local.sh
PYTHON=python3.11 VENV=.venv-py311 bash scripts/check-local.sh
PYTHON=python3.12 VENV=.venv-py312 bash scripts/check-local.sh
PYTHON=python3.13 VENV=.venv-py313 bash scripts/check-local.sh
```

The default is `PYTHON=python3` with `VENV=.venv`. Before package installation or
test execution, the runner verifies that any reused virtualenv has the same
underlying executable, implementation, and major/minor Python version as
`PYTHON`. A mismatch fails closed with an actionable diagnostic; it never
silently reports that another interpreter was tested. Choose a different
`VENV` for that interpreter rather than deleting an existing environment.

Run `bash tests/test_check_local_venv.sh` to exercise the selection and
mismatch guard in isolated mocked environments without network access.

No hosted GitHub Actions workflows remain. The full interpreter matrix must
still be run on a suitable developer host; the mocked regression test does
not replace real installs, Ruff, and pytest on each supported Python version.
