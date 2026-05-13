# Study.Py — Finance Edition

対話型 Python 学習デスクトップアプリ。金融計算（期待値・分散・トラッキングエラー・シャープレシオ・ポートフォリオ最適化・モンテカルロ）から時系列・ML/DL・Streamlit・自動操作まで、26 章でステップアップできる。副次目標として証券アナリスト（CMA）試験での数理・統計・ポートフォリオ理論の定着補助。

## 動作要件

- Windows / macOS / Linux
- Python 3.11+
- メモリ 1GB（PyTorch 章は 2GB+）
- [uv](https://docs.astral.sh/uv/) (パッケージマネージャ)

## セットアップ

`uv` がインストール済みであることを前提とします（未インストールなら `winget install astral-sh.uv` / `brew install uv` / `curl -LsSf https://astral.sh/uv/install.sh | sh`）。

```bash
cd study_python_finance

# 仮想環境 (.venv) を作成 + 全依存を同期
uv sync

# オプション機能を含めて一括導入
uv sync --extra dev --extra streamlit --extra automation
# 深層学習章を使うとき
uv sync --extra deep
# Playwright 章を使うとき (Chromium をローカルにインストール)
uv run playwright install chromium
```

## 起動

```bash
uv run python -m app.main
```

## 開発者向け

```bash
# テスト
uv run pytest

# Lint / フォーマット
uv run ruff check .
uv run ruff format .
uv run mypy app/

# 依存追加
uv add some-package          # 通常依存
uv add --optional dev pytest # オプション依存に追加
```

## ディレクトリ

```
app/                  # アプリ本体 (PyQt6 UI + Jupyter kernel + Pydantic + SQLAlchemy)
content/chapters/     # 章定義 YAML（学生は編集しない）
content/tests/        # 実力テスト問題集
data/                 # 各章のサンプル CSV / HTML
tests/                # pytest（コアロジック）
scripts/              # 章 YAML 一括生成スクリプト
```

## オプション機能

`.env` に `ANTHROPIC_API_KEY` を設定すると結果ページに「Ask AI」ボタンが表示され、Claude API による詳細解説が呼べます。未設定でも全機能オフラインで動作。

## ライセンス

MIT
