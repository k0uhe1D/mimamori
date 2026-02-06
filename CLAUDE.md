# mimamori

新生児モニタリングシステム。Android (Iriun Webcam) → Raspi 5 (8GB) → Cloud LLM。

## 開発ルール

### Git / GitHub ワークフロー
- **PR ベース開発**: 必ずブランチを切り、PR を作成する。main への直接 push 禁止。
- **ブランチ命名**: `feat/<issue番号>-<短い説明>`, `fix/<issue番号>-<短い説明>`, `chore/<説明>`
- **PR 粒度**: 1 PR = 1 つの論理的変更。300行を超えそうなら分割を検討する。
- **PR が大きくなった場合**: 即座に作業を止め、現在の変更をコミットし、残りの作業を別ブランチ・別 PR に分割する。
- **コミットメッセージ**: Conventional Commits 形式 (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`)
- **PR 作成後**: OpenAI Codex がレビューするため、明確な PR description を書く。

### タスク管理
- タスクや TODO は GitHub Issues に作成する。
- バグ発見時は即座に GitHub Issue を作成し、適切なラベルを付与する。
- GitHub Projects Board でタスクを管理する。

### CI/CD
- テスト・リント・デプロイは GitHub Actions で実行する。
- PR には CI チェックを必須とする。

### コード品質
- Python: ruff (lint + format), mypy (型チェック), pytest (テスト)
- 型ヒントを必ず付ける。
- docstring を関数・クラスに付ける。

### ディレクトリ構成
```
mimamori/
├── src/
│   ├── capture/      # 映像取得モジュール
│   ├── recorder/     # 録画モジュール
│   ├── analyzer/     # LLM 解析モジュール
│   ├── notifier/     # 通知モジュール（将来）
│   └── config/       # 設定管理
├── tests/
├── scripts/          # ユーティリティスクリプト
├── .github/
│   ├── workflows/    # GitHub Actions
│   └── ISSUE_TEMPLATE/
├── docs/
├── CLAUDE.md
└── pyproject.toml
```
