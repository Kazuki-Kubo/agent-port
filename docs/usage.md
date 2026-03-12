# 使い方

## セットアップ
依存関係は `uv` で入れます。

```powershell
uv sync --dev
```

次に `.env.example` を参考に `.env` を作成し、`config/workspaces.json.example` を参考に `config/workspaces.json` を作成します。

## 主な環境変数
- `AGENT_PORT_CHAT_BACKEND`: 現在は `discord`
- `AGENT_PORT_DISCORD_BOT_TOKEN`: Discord Bot token
- `AGENT_PORT_DISCORD_APPLICATION_ID`: Discord application ID
- `AGENT_PORT_DISCORD_TRIGGER_MODE`: `mention` または `all`
- `AGENT_PORT_WORKSPACE_REGISTRY`: workspace registry JSON の相対パス
- `AGENT_PORT_DEFAULT_WORKSPACE`: 既定 workspace ID
- `AGENT_PORT_DEFAULT_AGENT`: 既定 agent backend。現在は `codex`
- `AGENT_PORT_CODEX_COMMAND`: Codex CLI コマンド
- `AGENT_PORT_CODEX_TIMEOUT_SECONDS`: Codex 実行タイムアウト秒数
- `AGENT_PORT_LOG_LEVEL`: 例 `INFO`

`config/workspaces.json` には `workspace_id -> path` を定義します。`path` は registry ファイル基準の相対パスまたは絶対パスで書けます。ただし、`agent-port` 本体ディレクトリやその配下は指定できません。

## workspace registry 例
```json
{
  "workspaces": [
    {
      "id": "sample",
      "path": "../../workspace/sample",
      "allowed_agents": ["codex"],
      "description": "サンプル workspace"
    }
  ]
}
```

## 起動
```powershell
uv run python main.py
```

返答は Agent が選びます。現在の Codex 実装では、返答の 1 行目に `[delivery:reply]` または `[delivery:thread]` を出す契約にしてあり、Discord 側がそれを解釈して通常返信かスレッド返信を切り替えます。

## テスト
```powershell
uv run pytest
```
