# SOUK への貢献

コントリビューションに興味を持っていただきありがとうございます！このガイドで始め方を説明します。

[English](CONTRIBUTING.md) | [中文](CONTRIBUTING.zh.md)

## 開発環境のセットアップ

```bash
git clone https://github.com/NITI-Lab/SOUK.git
cd SOUK
python -m venv .venv
source .venv/bin/activate  # Windows の場合: .venv\Scripts\activate
pip install -e ".[dev]"
```

## ワークフロー

1. リポジトリを **Fork** する
2. `main` から **フィーチャーブランチ** を作成 (`git checkout -b feat/my-feature`)
3. 変更を加える
4. lint とテストを実行:
   ```bash
   ruff check src/ tests/
   ruff format src/ tests/
   pytest tests/ -v
   ```
5. わかりやすいメッセージで **コミット**
6. Fork にプッシュし、**Pull Request** を作成

> `main` ブランチへの直接プッシュはできません。すべての変更は PR レビューを経る必要があります。

## 評価基準の追加

1. `src/souk/criteria/` に新しいファイルを作成（例: `my_criterion.py`）
2. **3言語すべて** に対して `Criterion` オブジェクトを定義: `en`, `ja`, `zh`
3. `src/souk/criteria/registry.py` に登録
4. `tests/test_criteria.py` にテストを追加

## テストケースの追加

テストケースは `cases/<カテゴリ>/<言語>/` に配置します。各 YAML ファイルには以下が必要です:

```yaml
id: unique_case_id
name: "わかりやすい名前"
language: ja          # en, ja, zh のいずれか
category: recommendation  # naturalness, recommendation, security など
criteria:
  - recommendation
  - naturalness
conversation:         # 静的ケースの場合
  - role: user
    content: "..."
  - role: assistant
    content: "..."
# ライブケースの場合:
# user_turns:
#   - "最初のメッセージ"
#   - "2番目のメッセージ"
```

## コードスタイル

- リンターとフォーマッターには [Ruff](https://docs.astral.sh/ruff/) を使用
- 行の長さ: 120文字
- 型ヒントを推奨
- コードベースの既存パターンに従う

## コミットメッセージ

明確でわかりやすいコミットメッセージを使用してください:
- `feat: 商品比較基準を追加`
- `fix: runner で空の会話を処理`
- `docs: 中国語 README を更新`
- `test: 家電推薦のケースを追加`
