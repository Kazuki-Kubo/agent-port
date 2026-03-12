# 使い方

## セットアップ
開発環境は `uv` で作成します。

```powershell
uv sync --dev
```

## 実行
アプリケーションは次のコマンドで起動します。

```powershell
uv run python main.py
```

現時点では、標準出力に挨拶メッセージを表示します。

## 設定方針
将来的な実運用では、チャット実装、Agent 実装、Agent workspace を設定で切り替えます。

- `chat_backend`: 例 `discord`
- `agent_backend`: 例 `codex`
- `agent_workspace`: Agent を実行する workspace の相対パス

workspace のパスは、環境移動しやすいように相対パスで管理します。

## テスト
自動テストは `pytest` で実行します。

```powershell
uv run pytest
```

## 更新ルール
操作手順、実行例、開発フローに変更があった場合は、このファイルを更新してください。パスを記載するときは、リポジトリ基準の相対パスを使ってください。
