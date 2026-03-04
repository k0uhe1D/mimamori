# 拡張ガイド

このドキュメントは、mimamori を拡張する際の最小手順をまとめています。

## 1. カメラ入力を追加する

カメラ生成は `src/capture/factory.py` の `create_camera()` に集約されています。

### 追加手順

1. `src/capture/` に新しいカメラクラスを追加（`read_frame()` / `release()` 実装）
2. `create_camera()` の分岐に追加
3. `tests/test_camera_factory.py` にテストケースを追加

## 2. HTTP スナップショット URL の差分に対応する

古い Android の IP カメラアプリは、スナップショットエンドポイントが異なる場合があります。

- 例: `/shot.jpg`, `/photo.jpg`, `/image.jpg`

`CAMERA_URL` がベース URL の場合、`CAMERA_HTTP_SNAPSHOT_PATH` を連結して使用します。  
`CAMERA_URL` がフルパスの場合はそのまま使用します。

## 3. LLM プロバイダを追加する

LLM 呼び出しは `src/__main__.py` のルーティングで切り替えています。

### 追加手順

1. `src/analyzer/` に新しいクライアントを追加
2. `_call_analyzer()` と Web 実行時ルーティングに分岐を追加
3. `src/config/settings.py` の `LLM_PROVIDER` 検証にプロバイダ名を追加
4. 必要な API キー環境変数を `.env.example` と README に追記

## 4. API/画面を追加する

- API スキーマ: `src/web/schemas.py`
- API 実装: `src/web/app.py`
- UI テンプレート: `src/web/templates/index.html`

API 追加時は `tests/test_web_app.py` にエンドポイントテストを追加してください。
