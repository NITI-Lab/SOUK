# 为 SOUK 做贡献

感谢您有兴趣为本项目做贡献！本指南将帮助您快速上手。

[English](CONTRIBUTING.md) | [日本語](CONTRIBUTING.ja.md)

## 开发环境设置

```bash
git clone https://github.com/NITI-Lab/SOUK.git
cd SOUK
python -m venv .venv
source .venv/bin/activate  # Windows 用户: .venv\Scripts\activate
pip install -e ".[dev]"
```

## 工作流程

1. **Fork** 本仓库
2. 从 `main` 创建**功能分支** (`git checkout -b feat/my-feature`)
3. 进行修改
4. 运行代码检查和测试:
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   pytest tests/ -v
   ```
5. 使用清晰的描述性消息进行 **提交**
6. **推送**到您的 Fork 并创建 **Pull Request**

> 不允许直接推送到 `main` 分支。所有更改必须通过 PR 审查。

## 添加评估标准

1. 在 `src/chat_eval/criteria/` 中创建新文件（例如 `my_criterion.py`）
2. 为**所有三种语言**定义 `Criterion` 对象: `en`, `ja`, `zh`
3. 在 `src/chat_eval/criteria/registry.py` 中注册
4. 在 `tests/test_criteria.py` 中添加测试

## 添加测试用例

测试用例存放在 `cases/<类别>/<语言>/` 目录下。每个 YAML 文件需要包含:

```yaml
id: unique_case_id
name: "易于理解的名称"
language: zh          # en、ja 或 zh
category: recommendation  # naturalness、recommendation、security 等
criteria:
  - recommendation
  - naturalness
conversation:         # 静态用例
  - role: user
    content: "..."
  - role: assistant
    content: "..."
# 实时用例:
# user_turns:
#   - "第一条消息"
#   - "第二条消息"
```

## 代码风格

- 使用 [Ruff](https://docs.astral.sh/ruff/) 进行代码检查和格式化
- 行长度限制: 120 个字符
- 鼓励使用类型注解
- 遵循代码库中的现有模式

## 提交消息

使用清晰、描述性的提交消息:
- `feat: 添加产品比较标准`
- `fix: 处理 runner 中的空对话`
- `docs: 更新中文 README`
- `test: 添加电子产品推荐测试用例`
