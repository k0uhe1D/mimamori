---
name: github-issue
description: "バグ発見時やタスク作成時に GitHub Issue を作成する。'issue', 'バグ', 'タスク', 'TODO' といったキーワードで自動起動。"
---

# GitHub Issue 作成

## 手順
1. Issue のタイトルと本文を作成
2. 適切なラベルを付与 (bug, enhancement, documentation, etc.)
3. GitHub Projects Board に紐付け
4. `gh issue create` で作成

## コマンド例
```bash
gh issue create \
  --title "タイトル" \
  --body "## 概要\n\n## 再現手順\n\n## 期待動作\n\n## 実際の動作" \
  --label "bug" \
  --project "mimamori"
```
