# 使い方

## セットアップ
まず `uv` で依存を入れます。

```powershell
uv sync --dev
```

次に雛形ファイルを配置します。

```powershell
uv run agent-port setup
```

生成されるファイル:
- `.env`
- `config/workspaces.json`

既存の `.env` は秘密情報保護のため上書きしません。`uv run agent-port setup --force` は `config/workspaces.json` のような一般設定ファイルだけを上書きします。

## 主な環境変数
- `AGENT_PORT_CHAT_BACKEND`: 現在は `discord`
- `AGENT_PORT_DISCORD_BOT_TOKEN`: Discord Bot token
- `AGENT_PORT_DISCORD_APPLICATION_ID`: Discord application ID
- `AGENT_PORT_DISCORD_TRIGGER_MODE`: `mention` または `all`
- `AGENT_PORT_WORKSPACE_REGISTRY`: workspace registry JSON の相対パス
- `AGENT_PORT_DEFAULT_WORKSPACE`: 既定 workspace ID
- `AGENT_PORT_DEFAULT_AGENT`: 既定 Agent backend。現在は `codex`
- `AGENT_PORT_CODEX_COMMAND`: Codex CLI コマンド
- `AGENT_PORT_CODEX_TIMEOUT_SECONDS`: Codex 実行タイムアウト秒数
- `AGENT_PORT_LOG_LEVEL`: 例 `INFO`

## workspace registry
`config/workspaces.json` には `workspace_id -> path` を定義します。`path` は registry ファイル基準の相対パスまたは絶対パスで書けます。

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

workspace は `agent-port` 本体 repo の外を指定してください。

## 診断
設定後は次の順で確認します。

```powershell
uv run agent-port doctor
uv run agent-port config validate
uv run agent-port workspace list
```

## 起動
```powershell
uv run agent-port gateway
```

`mention` モードでは Bot 本体または Bot ロールへのメンション付きメッセージだけを受け付けます。Codex からの返答 1 行目に `[delivery:reply]` または `[delivery:thread]` がある場合、その指示に従って Discord へ返します。

## テスト
```powershell
uv run pytest
```
