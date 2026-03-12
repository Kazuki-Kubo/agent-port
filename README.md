# agent-port

`agent-port` は、Discord などのチャットツールと Codex CLI などの Agent を中継する control plane です。最小構成では `Discord -> AgentRouter -> CodexRunner` を提供し、OpenClaw に近い操作感で設定確認、workspace 管理、Gateway 起動を行えます。

## ドキュメント
- `docs/usage.md`: セットアップと日常操作
- `docs/specs.md`: 仕様の入口
- `docs/specs/`: 詳細仕様

## セットアップ
```powershell
uv sync --dev
uv run agent-port setup
```

`setup` は `.env.example` を `.env` に、`config/workspaces.json.example` を `config/workspaces.json` にコピーします。既存の `.env` は秘密情報保護のため上書きしません。`--force` を付けた場合でも、上書き対象は `config/workspaces.json` のような一般設定ファイルだけです。

次に `.env` と `config/workspaces.json` を編集します。workspace はこの repo の外にある作業対象ディレクトリを指定してください。`agent-port` 本体やその配下は workspace にできません。

## 診断と確認
```powershell
uv run agent-port doctor
uv run agent-port config show
uv run agent-port workspace list
```

`doctor` は `.env`、workspace registry、Codex CLI の解決可否をまとめて確認します。`config show` は現在の設定、`workspace list` は登録済み workspace 一覧を表示します。

## 起動
```powershell
uv run agent-port gateway
```

`AGENT_PORT_DISCORD_TRIGGER_MODE=mention` の場合は Bot 本体または Bot ロールへのメンション付きメッセージに反応します。`all` の場合は通常メッセージにも反応します。

## テスト
```powershell
uv run pytest
```

## 主な設定
- `AGENT_PORT_WORKSPACE_REGISTRY=config/workspaces.json`
- `AGENT_PORT_DEFAULT_WORKSPACE=sample`
- `AGENT_PORT_DEFAULT_AGENT=codex`
- `AGENT_PORT_CODEX_COMMAND=codex`

後方互換として `AGENT_PORT_CODEX_WORKSPACE` と `AGENT_PORT_AGENT_WORKSPACE` も読めますが、今後は workspace registry の利用を前提にしてください。
