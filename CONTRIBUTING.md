# Contributing

Thanks for your interest in improving **tc-qa-checker**.

## Local setup

```bash
git clone https://github.com/rahulchandravanshi/tc-qa-checker
cd tc-qa-checker
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
pre-commit install
```

## Checks

Run these before opening a pull request — CI runs the same set:

```bash
ruff check src tests
ruff format --check src tests
mypy --strict src
pytest -v --cov=src --cov-report=term-missing
```

## Pull requests

- Branch off `main`.
- Keep commits small and scoped; use
  [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `ci:`).
- Make sure CI is green and test coverage does not regress.
- Never include client data, internal/employer names, or secrets in code, tests, or commits.
