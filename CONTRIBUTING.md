# Contributing

## Local checks

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[dev]'
ruff check .
pytest
```

## Hardware captures

Do not commit proprietary firmware or private network data. When recording a printer response,
redact MAC addresses and public IP addresses. Prefer adding the smallest response fixture that
reproduces a parser or protocol difference.

## Safety

Physical-printer tests should begin with `probe` and `status`. Upload without `--start` first.
Use a small, reviewed G-code file for the first print-start test.
