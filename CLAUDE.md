# mimamori

新生児モニタリングシステム。Android (Iriun Webcam) → Raspi 5 (8GB) → Cloud LLM。

## 開発ルール

### Git ブランチ戦略（軽量 Gitflow）

- **main**: 本番（Raspi デプロイ）。直接 push 禁止。
- **develop**: 統合ブランチ。feature/fix ブランチの PR 先。
- **feat/**, **fix/**: develop から切り、develop に PR を出す。
- **リリース**: develop が安定したら develop → main へ PR。

```
main（本番: Raspi にデプロイされる安定版）
  └── develop（統合ブランチ: エージェントの成果物をここにマージ）
        ├── feat/1-capture  (Claude Code Agent A)
        ├── feat/2-recorder (Claude Code Agent B)
        └── feat/3-analyzer (Codex Agent C)
```

### 複数エージェント同時作業時の注意
- 各エージェントは作業開始前に `develop` を最新化する。
- モジュール境界（capture / recorder / analyzer）で作業を分割し、同一ファイルへの同時変更を避ける。

### Git / GitHub ワークフロー
- **PR ベース開発**: 必ずブランチを切り、PR を作成する。main・develop への直接 push 禁止。
- **ブランチ命名**: `feat/<issue番号>-<短い説明>`, `fix/<issue番号>-<短い説明>`, `chore/<説明>`
- **PR 先**: feature/fix ブランチ → develop。リリース時のみ develop → main。
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
