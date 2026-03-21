<div align="center">

# SOUK

**Open-source benchmark for evaluating EC product recommendation chat quality**

[![CI](https://github.com/NITI-Lab/SOUK/actions/workflows/ci.yml/badge.svg)](https://github.com/NITI-Lab/SOUK/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/souk.svg)](https://pypi.org/project/souk/)

[Japanese (日本語)](README.ja.md) | [Chinese (中文)](README.zh.md)

</div>

---

SOUK evaluates how well your chat assistant recommends products, handles conversations naturally, and resists security attacks. It uses multiple AI models (GPT, Claude, Gemini) as judges to score conversations across configurable criteria.

## Features

- **Multi-model judging** — GPT-4o, Claude, Gemini, Bedrock, or any OpenAI-compatible endpoint as judges
- **10 built-in criteria** — naturalness, recommendation quality, coherence, hallucination, helpfulness, toxicity, prompt injection, info leakage, role boundary, PII handling
- **Trilingual** — All criteria and test cases available in English, Japanese, and Chinese
- **Static & live evaluation** — Evaluate pre-recorded conversations or test live endpoints
- **HTML + JSON reports** — Visual dashboards with Chart.js and machine-readable JSON
- **MCP server** — Integrate evaluations into AI-powered development workflows
- **Docker ready** — Run evaluations in containers with zero setup

## Quick Start

```bash
pip install souk

# Configure judges and run
souk run config.yaml

# List available test cases
souk list-cases ./cases

# List evaluation criteria
souk list-criteria

# Discover available models from your configured providers
souk models
```

## Installation

```bash
# Basic
pip install souk

# With MCP server support
pip install "souk[mcp]"

# With AWS Bedrock support
pip install "souk[bedrock]"

# Everything
pip install "souk[all]"
```

## Configuration

```bash
cp config.example.yaml config.yaml
cp .env.example .env
# Edit .env with your API keys
souk run config.yaml
```

See [config.example.yaml](config.example.yaml) for all available options.

## Docker

```bash
cp config.example.yaml config.yaml
# Set API keys in .env
docker compose up souk
```

## How It Works

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Test Cases  │────▶│  SOUK Runner │────▶│   Reports   │
│  (YAML)      │     │              │     │  HTML/JSON   │
└─────────────┘     │  ┌─────────┐ │     └─────────────┘
                     │  │ Judge 1 │ │
┌─────────────┐     │  │ (GPT-4o)│ │
│   Target     │────▶│  ├─────────┤ │
│  (optional)  │     │  │ Judge 2 │ │
│  Live chat   │     │  │ (Claude)│ │
└─────────────┘     │  ├─────────┤ │
                     │  │ Judge 3 │ │
                     │  │(Gemini) │ │
                     │  └─────────┘ │
                     └──────────────┘
```

1. **Load** test cases from YAML files (static conversations or live user turns)
2. **Run** each conversation through multiple AI judge models
3. **Score** against selected criteria (0-10 scale with detailed rubrics)
4. **Generate** HTML dashboards and JSON reports

## Writing Test Cases

### Static (pre-recorded conversation)

```yaml
id: laptop_recommendation
name: Laptop Recommendation for Designer
language: en
category: recommendation
criteria:
  - recommendation
  - naturalness
conversation:
  - role: user
    content: "I need a laptop for graphic design, budget $1500"
  - role: assistant
    content: "For graphic design at that budget, I'd suggest..."
```

### Live (evaluate your endpoint)

```yaml
id: live_product_search
name: Live Product Search Test
language: en
category: recommendation
criteria:
  - recommendation
  - helpfulness
user_turns:
  - "I'm looking for running shoes"
  - "I run about 30km per week on pavement"
  - "My budget is around $150"
```

## Evaluation Criteria

| Criterion | Description |
|-----------|-------------|
| `naturalness` | How natural and human-like the conversation feels |
| `recommendation` | Quality of product/service recommendations |
| `coherence` | Logical consistency across conversation turns |
| `hallucination` | Detection of fabricated facts or entities |
| `helpfulness` | Whether the assistant effectively helps the user |
| `toxicity` | Detection of harmful or biased content |
| `prompt_injection` | Resistance to prompt injection attacks |
| `info_leakage` | Prevention of system prompt / internal data leakage |
| `role_boundary` | Maintaining designated role boundaries |
| `pii_handling` | Proper handling of personal information |

## MCP Server

SOUK can run as an MCP server for integration with AI coding tools:

```bash
python -m chat_eval.mcp.server
```

## Star History

<a href="https://star-history.com/#NITI-Lab/SOUK&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=NITI-Lab/SOUK&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=NITI-Lab/SOUK&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=NITI-Lab/SOUK&type=Date" />
 </picture>
</a>

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

> **Note:** Direct pushes to `main` are not allowed. All changes must go through pull request review.

## License

[MIT](LICENSE)
