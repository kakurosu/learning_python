# Study Python Finance

対話型 Python 学習デスクトップアプリ。金融計算（期待値・分散・トラッキングエラー・シャープレシオ・ポートフォリオ最適化・モンテカルロ）から時系列・ML/DL・Streamlit・自動操作まで、26 章でステップアップできる。副次目標として証券アナリスト（CMA）試験での数理・統計・ポートフォリオ理論の定着補助。

## 動作要件

- Windows / macOS / Linux
- Python 3.11+
- メモリ 1GB（PyTorch 章は 2GB+）

## セットアップ

```bash
cd study_python_finance
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -e ".[dev,streamlit,automation]"
# 深層学習章を使うとき: pip install -e ".[deep]"
# Playwright 章を使うとき: playwright install chromium
```

## 起動

```bash
python -m app.main
```

## ディレクトリ

```
app/                  # アプリ本体
content/chapters/     # 章定義 YAML（学生はここを触らない）
content/tests/        # 実力テスト問題集
data/                 # 章で使う CSV / HTML サンプル
tests/                # pytest（コアロジック）
```

## ライセンス

MIT
