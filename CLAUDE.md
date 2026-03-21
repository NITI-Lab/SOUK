# SOUK - Development Guide

## Project Overview
SOUK is an open-source benchmark for evaluating EC (e-commerce) product recommendation chat quality. It uses multiple AI judge models to score conversations.

## Quick Commands
```bash
# Install for development
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/
ruff format src/ tests/

# Run evaluation
souk run config.yaml

# Docker
docker compose up souk
```

## Architecture
- `src/chat_eval/` - Core Python package
  - `cli.py` - Click CLI entry point
  - `config.py` - Pydantic config models
  - `runner.py` - Evaluation orchestrator
  - `criteria/` - Evaluation criteria (en/ja/zh)
  - `judges/` - Judge implementations (OpenAI, Anthropic, Google, Bedrock, Endpoint)
  - `report/` - HTML/JSON report generation
  - `mcp/` - MCP server integration
- `cases/` - YAML test cases organized by category/language
- `tests/` - pytest test suite

## Conventions
- All evaluation criteria must support three languages: en, ja, zh
- Test cases are YAML with required fields: id, name, language, category, criteria
- CLI entry point is `souk` (mapped to `chat_eval.cli:main`)
