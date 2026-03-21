# Contributing to SOUK

Thank you for your interest in contributing! This guide will help you get started.

[日本語](CONTRIBUTING.ja.md) | [中文](CONTRIBUTING.zh.md)

## Development Setup

```bash
git clone https://github.com/NITI-Lab/SOUK.git
cd SOUK
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Workflow

1. **Fork** the repository
2. Create a **feature branch** from `main` (`git checkout -b feat/my-feature`)
3. Make your changes
4. Run lint & tests:
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   pytest tests/ -v
   ```
5. **Commit** with a descriptive message
6. **Push** to your fork and open a **Pull Request**

> Direct pushes to `main` are not allowed. All changes go through PR review.

## Adding Evaluation Criteria

1. Create a new file in `src/chat_eval/criteria/` (e.g., `my_criterion.py`)
2. Define `Criterion` objects for **all three languages**: `en`, `ja`, `zh`
3. Register them in `src/chat_eval/criteria/registry.py`
4. Add tests in `tests/test_criteria.py`

## Adding Test Cases

Test cases live in `cases/<category>/<language>/`. Each YAML file needs:

```yaml
id: unique_case_id
name: "Human-readable Name"
language: en          # en, ja, or zh
category: recommendation  # naturalness, recommendation, security, etc.
criteria:
  - recommendation
  - naturalness
conversation:         # for static cases
  - role: user
    content: "..."
  - role: assistant
    content: "..."
# OR for live cases:
# user_turns:
#   - "first message"
#   - "second message"
```

## Code Style

- We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting
- Line length: 120 characters
- Type hints are encouraged
- Follow existing patterns in the codebase

## Commit Messages

Use clear, descriptive commit messages:
- `feat: add product comparison criterion`
- `fix: handle empty conversation in runner`
- `docs: update Chinese README`
- `test: add cases for electronics recommendation`
