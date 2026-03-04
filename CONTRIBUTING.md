# Contributing Guide

mimamori への貢献ありがとうございます。  
このドキュメントでは、開発参加時の最低限のルールをまとめています。

## 開発環境

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## ブランチ運用

- `main`: リリース用
- `develop`: 統合用
- 作業ブランチ: `feat/<topic>` または `fix/<topic>`

## コーディング規約

- Python 3.12+
- 型ヒントを付与する
- 既存コードの命名・設計方針に合わせる
- 変更は小さく、論理単位で分割する

## 変更前チェック

```bash
ruff check .
ruff format --check .
mypy src/
pytest -v
```

## Pull Request

- 目的と背景を明確に記載する
- 変更内容を箇条書きで記載する
- テスト結果を記載する
- 破壊的変更がある場合は明記する

## Issue

- バグ報告時は、再現手順・期待値・実際の挙動を記載してください
- 機能提案時は、ユースケースと効果を記載してください

## セキュリティ

脆弱性報告は公開 Issue ではなく、[SECURITY.md](SECURITY.md) の手順に従ってください。
