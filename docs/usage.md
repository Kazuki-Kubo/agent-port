# 使い方

## セットアップ
依存関係は `uv` で入れます。

```powershell
uv sync --dev
```

次に `.env.example` をコピーして `.env` を作成します。`.env` は共有せず、秘密値を含まない例だけを `.env.example` に残します。

## 主な環境変数
- `AGENT_PORT_CHAT_BACKEND`: 現在は `discord` を使用
- `AGENT_PORT_DISCORD_BOT_TOKEN`: Discord Bot トークン
- `AGENT_PORT_DISCORD_APPLICATION_ID`: Discord アプリケーション ID
- `AGENT_PORT_DISCORD_TRIGGER_MODE`: `mention` または `all`
- `AGENT_PORT_DEFAULT_AGENT`: 既定の Agent。現時点では `codex`
- `AGENT_PORT_CODEX_WORKSPACE`: Codex を実行する workspace。相対パスまたは絶対パス
- `AGENT_PORT_CODEX_COMMAND`: Codex CLI コマンド。通常は `codex`
- `AGENT_PORT_CODEX_TIMEOUT_SECONDS`: Codex 実行タイムアウト秒数
- `AGENT_PORT_LOG_LEVEL`: 例 `INFO`

`AGENT_PORT_AGENT_BACKEND` と `AGENT_PORT_AGENT_WORKSPACE` も読めますが、これは旧設定との互換用です。新しい設定では `AGENT_PORT_DEFAULT_AGENT` と `AGENT_PORT_CODEX_WORKSPACE` を使います。

## 起動
```powershell
uv run python main.py
```

起動後、`mention` モードでは Bot 本体か Bot ロールをメンションしたメッセージだけを処理します。`all` モードでは通常メッセージも処理します。返答は元メッセージへの返信として同じチャンネルに返します。

## テスト
```powershell
uv run pytest
```
