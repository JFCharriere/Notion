# CLAUDE.md

## Project Overview

Python application (Python 3.10).

## Development Commands

### Install Dependencies

```bash
pip install flake8 pytest
pip install -r requirements.txt  # if requirements.txt exists
```

### Linting

```bash
# Strict check for syntax errors and undefined names
flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics

# Full lint (warnings, style)
flake8 . --count --exit-zero --max-complexity=10 --max-line-length=127 --statistics
```

### Testing

```bash
pytest
```

## Code Style

- Max line length: 127 characters
- Max cyclomatic complexity: 10
- Linter: flake8
- Follow PEP 8 conventions

## CI/CD

GitHub Actions workflow runs on push/PR to `main`:
1. Install dependencies
2. Lint with flake8
3. Test with pytest
