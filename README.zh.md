<div align="center">

# SOUK

**评估电商产品推荐聊天质量的开源基准**

[![CI](https://github.com/NITI-Lab/SOUK/actions/workflows/ci.yml/badge.svg)](https://github.com/NITI-Lab/SOUK/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![PyPI version](https://img.shields.io/pypi/v/souk.svg)](https://pypi.org/project/souk/)

[English](README.md) | [日本語](README.ja.md)

</div>

---

SOUK 评估聊天助手推荐产品的能力、对话的自然程度以及对安全攻击的抵抗能力。它使用多个 AI 模型（GPT、Claude、Gemini）作为评委，按照可配置的标准为对话评分。

## 功能特性

- **多模型评审** — 使用 GPT-4o、Claude、Gemini、Bedrock 或任何兼容 OpenAI 的端点作为评委
- **10 项内置评估标准** — 自然度、推荐质量、连贯性、幻觉检测、有用性、有害性、提示注入、信息泄露、角色边界、PII 处理
- **三语支持** — 所有评估标准和测试用例均支持英语、日语和中文
- **静态和实时评估** — 评估预先录制的对话或测试实时端点
- **HTML + JSON 报告** — 使用 Chart.js 的可视化仪表板和机器可读的 JSON
- **MCP 服务器** — 集成到 AI 驱动的开发工作流程中
- **Docker 就绪** — 零配置在容器中运行评估

## 快速开始

```bash
pip install souk

# 配置评委并运行
souk run config.yaml

# 列出可用的测试用例
souk list-cases ./cases

# 列出评估标准
souk list-criteria

# 发现可用模型
souk models
```

## 安装

```bash
# 基础安装
pip install souk

# 包含 MCP 服务器支持
pip install "souk[mcp]"

# 包含 AWS Bedrock 支持
pip install "souk[bedrock]"

# 全部功能
pip install "souk[all]"
```

## 配置

```bash
cp config.example.yaml config.yaml
cp .env.example .env
# 在 .env 中编辑您的 API 密钥
souk run config.yaml
```

详细信息请参阅 [config.example.yaml](config.example.yaml)。

## Docker

```bash
cp config.example.yaml config.yaml
# 在 .env 中设置 API 密钥
docker compose up souk
```

## 工作原理

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   测试用例    │────▶│  SOUK Runner │────▶│    报告      │
│   (YAML)     │     │              │     │  HTML/JSON   │
└─────────────┘     │  ┌─────────┐ │     └─────────────┘
                     │  │ 评委 1  │ │
┌─────────────┐     │  │ (GPT-4o)│ │
│    目标       │────▶│  ├─────────┤ │
│  （可选）      │     │  │ 评委 2  │ │
│  实时聊天     │     │  │ (Claude)│ │
└─────────────┘     │  ├─────────┤ │
                     │  │ 评委 3  │ │
                     │  │(Gemini) │ │
                     │  └─────────┘ │
                     └──────────────┘
```

1. 从 YAML 文件**加载**测试用例（静态对话或实时用户回合）
2. 通过多个 AI 评委模型**运行**每个对话
3. 按选定标准进行**评分**（0-10 分制，附详细评分标准）
4. **生成** HTML 仪表板和 JSON 报告

## 编写测试用例

### 静态（预先录制的对话）

```yaml
id: laptop_recommendation
name: 为设计师推荐笔记本电脑
language: zh
category: recommendation
criteria:
  - recommendation
  - naturalness
conversation:
  - role: user
    content: "我需要一台用于图形设计的笔记本电脑，预算1万元"
  - role: assistant
    content: "在这个预算范围内做图形设计，我建议..."
```

### 实时（评估您的端点）

```yaml
id: live_product_search
name: 实时商品搜索测试
language: zh
category: recommendation
criteria:
  - recommendation
  - helpfulness
user_turns:
  - "我在找跑步鞋"
  - "我每周在柏油路上跑30公里"
  - "预算大概1000元"
```

## 评估标准

| 标准 | 说明 |
|------|------|
| `naturalness` | 对话的自然程度和人性化程度 |
| `recommendation` | 产品/服务推荐的质量 |
| `coherence` | 对话轮次间的逻辑一致性 |
| `hallucination` | 检测捏造的事实或实体 |
| `helpfulness` | 助手是否有效地帮助用户实现目标 |
| `toxicity` | 检测有害或偏见内容 |
| `prompt_injection` | 对提示注入攻击的抵抗能力 |
| `info_leakage` | 防止系统提示/内部数据泄露 |
| `role_boundary` | 维护指定的角色边界 |
| `pii_handling` | 正确处理个人信息 |

## MCP 服务器

SOUK 可以作为 MCP 服务器运行，与 AI 编码工具集成：

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

## 贡献

欢迎贡献！请参阅 [CONTRIBUTING.md](CONTRIBUTING.md) 了解指南。

> **注意：** 不允许直接推送到 `main` 分支。所有更改必须通过拉取请求审查。

## 许可证

[MIT](LICENSE)
