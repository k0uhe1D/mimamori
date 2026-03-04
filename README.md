# mimamori

新生児の見守りを支援する、Raspberry Pi ベースのモニタリングシステムです。  
ローカルで映像取得・状態管理を行い、クラウド LLM（OpenAI / Gemini）で画像解析します。

## コンセプト

ベビーカメラ専用機器を新規購入しなくても、手元の古い Android 端末を IP カメラ化して再利用できることを重視しています。

- 既存端末の再利用で導入コストを抑える
- Raspberry Pi 側で録画・状態管理を行う
- LLM 解析で「常時監視の補助」を行う

## このリポジトリの位置づけ

- OSS: 実装・設計の透明性を重視した公開リポジトリ
- ポートフォリオ: カメラ入力、バックグラウンド処理、Web ダッシュボード、永続化、テスト整備までを一貫して実装

## 主な機能

- ローカルカメラ / RTSP / HTTP カメラ入力
- 画像フレームの定期解析（OpenAI / Gemini 切替）
- Web ダッシュボード表示（FastAPI + Jinja2）
- 睡眠状態トラッキング
- 録画制御
- SQLite ベースの状態保存

## アーキテクチャ概要

```text
Camera (Local / RTSP / HTTP)
  -> Frame Grabber
  -> Analyzer Worker (OpenAI or Gemini)
  -> Monitoring State / Sleep Tracker
  -> SQLite Repository
  -> FastAPI Web UI
```

詳細仕様は [docs/SPECIFICATION.md](docs/SPECIFICATION.md) を参照してください。  
拡張方法は [docs/EXTENDING.md](docs/EXTENDING.md) を参照してください。

## 動作環境

- Python 3.12+
- macOS / Linux（Raspberry Pi を想定）
- カメラ入力デバイス（任意）
- OpenAI または Gemini の API キー

## セットアップ

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

`.env` に必要な値を設定後、環境変数を読み込んで実行してください。

## 環境変数

| 変数名 | 必須 | 説明 | 例 |
|---|---|---|---|
| `LLM_PROVIDER` | 必須 | `openai` または `gemini` | `openai` |
| `OPENAI_API_KEY` | 条件付き | `LLM_PROVIDER=openai` のとき必須 | `sk-...` |
| `GEMINI_API_KEY` | 条件付き | `LLM_PROVIDER=gemini` のとき必須 | `AIza...` |
| `CAMERA_DEVICE_INDEX` | 任意 | ローカルカメラのデバイス番号 | `0` |
| `CAMERA_URL` | 任意 | RTSP / HTTP カメラ URL（ベース URL も可） | `http://192.168.1.10:8080` |
| `CAMERA_HTTP_SNAPSHOT_PATH` | 任意 | HTTP ベース URL のスナップショットパス | `/shot.jpg` |
| `ANALYSIS_INTERVAL_SECONDS` | 任意 | 定期解析間隔（秒） | `5` |
| `CAPTURE_WIDTH` | 任意 | キャプチャ横幅 | `640` |
| `CAPTURE_HEIGHT` | 任意 | キャプチャ縦幅 | `480` |
| `OPENAI_MODEL` | 任意 | OpenAI のモデル名 | `gpt-4o` |
| `GEMINI_MODEL` | 任意 | Gemini のモデル名 | `gemini-2.5-flash` |

### 古い Android を IP カメラとして使う例

1. Android 端末で IP カメラアプリを起動（同一 LAN）
2. `CAMERA_URL` にベース URL を設定
3. 必要なら `CAMERA_HTTP_SNAPSHOT_PATH` をアプリ仕様に合わせる

```bash
export CAMERA_URL=\"http://192.168.1.10:8080\"
export CAMERA_HTTP_SNAPSHOT_PATH=\"/shot.jpg\"
python -m src --mode web
```

`CAMERA_URL` に `http://.../photo.jpg` のようなフルパスを指定した場合は、その URL をそのまま利用します。

## 拡張性

- カメラ生成は `src/capture/factory.py` に集約
- HTTP / RTSP / ローカル切替の分岐を 1 箇所で管理
- LLM 切替は `Settings.llm_provider` と実行時設定で切替可能
- Web API 経由でカメラソース・モデルをランタイム変更可能

## 実行方法

```bash
# 1回だけ解析
python -m src --mode oneshot

# 定期解析
python -m src --mode periodic

# Web ダッシュボード
python -m src --mode web
```

`pip install -e .` 後は、以下のエントリポイントも使えます。

```bash
mimamori --mode web
```

## テスト / 品質チェック

```bash
ruff check .
ruff format --check .
mypy src/
pytest -v
```

## セキュリティと注意事項

- このプロジェクトは医療機器ではありません
- 乳児の安全監視を完全に代替するものではありません
- 映像・ログには個人情報が含まれる可能性があります。公開・共有時は必ず匿名化してください
- 脆弱性報告は [SECURITY.md](SECURITY.md) を参照してください

## コントリビュート

参加方法は [CONTRIBUTING.md](CONTRIBUTING.md) を参照してください。  
行動規範は [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) に記載しています。

## ライセンス

MIT License（[LICENSE](LICENSE)）
