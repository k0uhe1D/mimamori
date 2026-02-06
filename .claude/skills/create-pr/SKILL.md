---
name: create-pr
description: "実装完了時に PR を作成する。ブランチ作成、コミット、push、PR 作成までを一貫して行う。"
---

# PR 作成ワークフロー

## 事前チェック
1. 変更差分が300行を超えていないか確認
2. 超えている場合は分割を提案

## 手順
1. ブランチ名: `feat/<issue番号>-<短い説明>` or `fix/<issue番号>-<短い説明>`
2. Conventional Commits でコミット
3. `git push origin <branch>`
4. `gh pr create` で PR 作成
   - タイトル: Conventional Commits 形式
   - 本文: 変更内容、関連 Issue、テスト結果を記載
   - レビュアー: OpenAI Codex がレビューするため description を詳細に

## PR テンプレート
タイトル: `feat(module): 簡潔な説明 (#issue番号)`

本文:
```markdown
## 概要
何を、なぜ変更したか

## 変更内容
- 変更点1
- 変更点2

## テスト
- [ ] ユニットテスト追加/更新
- [ ] CI パス確認

## 関連 Issue
Closes #XX
```
