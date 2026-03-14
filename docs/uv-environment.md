# UV Environment

This project should use a local Python 3.13 environment.

## Why
- host default Python is 3.14
- `vectorbt` currently depends on a `numba` stack that does not support Python 3.14 here
- Python 3.13 is the stable path for the intended research stack

## Setup
```bash
cd project
uv venv --python /opt/homebrew/bin/python3.13 .venv
source .venv/bin/activate
uv pip install -e .
```

## Verify
```bash
python --version
python -c "import vectorbt; print(vectorbt.__version__)"
```

## Rule
Do not use the host 3.14 environment for this project unless we intentionally change the stack.
