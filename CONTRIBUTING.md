# Contributing to scrubfile

Thanks for your interest in contributing!

## Setup

```bash
git clone https://github.com/scrubfile/scrubfile.git
cd scrubfile
pip install -e ".[dev]"
python -m spacy download en_core_web_lg  # required for auto-detect tests
```

## Running Tests

```bash
# Fast tests (no model downloads needed)
pytest tests/ -m "not slow"

# All tests (requires spaCy + EasyOCR models)
pytest tests/
```

## Code Style

- Python 3.10+ type hints
- Tests required for new features
- Keep PRs small and focused

## Pull Requests

1. Fork the repo and create a branch
2. Make your changes
3. Ensure tests pass: `pytest tests/ -m "not slow"`
4. Submit a PR with a clear description

## Reporting Issues

Use [GitHub Issues](https://github.com/scrubfile/scrubfile/issues). Include:
- scrubfile version (`pip show scrubfile`)
- Python version
- OS
- Minimal reproduction steps
