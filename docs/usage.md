# 使い方

## セットアップ
開発環境は `uv` で作成します。

```powershell
uv sync --dev
```

## 実行
アプリケーションは次のコマンドで起動します。

```powershell
$env:AGENT_PORT_DISCORD_BOT_TOKEN="your-bot-token"
$env:AGENT_PORT_AGENT_WORKSPACE="workspace/sample"
uv run python main.py
```

現時点では、読み込んだ設定サマリーを標準出力に表示します。

## 設定方針
将来的な実運用では、チャット実装、Agent 実装、Agent workspace を環境変数で切り替えます。

- `AGENT_PORT_CHAT_BACKEND`: 例 `discord`
- `AGENT_PORT_AGENT_BACKEND`: 例 `codex`
- `AGENT_PORT_DISCORD_BOT_TOKEN`: Discord Bot トークン
- `AGENT_PORT_DISCORD_APPLICATION_ID`: Discord アプリケーション ID
- `AGENT_PORT_AGENT_WORKSPACE`: Agent を実行する workspace の相対パス
- `AGENT_PORT_LOG_LEVEL`: 例 `INFO`

workspace のパスは、環境移動しやすいように相対パスで管理します。

## テスト
自動テストは `pytest` で実行します。

```powershell
uv run pytest
```

## 更新ルール
操作手順、実行例、開発フローに変更があった場合は、このファイルを更新してください。パスを記載するときは、リポジトリ基準の相対パスを使ってください。
