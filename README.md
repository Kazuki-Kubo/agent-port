# agent-port

`agent-port` は、Discord などのチャットツールと Codex CLI などの Agent を中継する control plane です。最小構成では `Discord -> Router -> CodexRunner` を提供し、OpenClaw に近い流れで設定確認、workspace 管理、Gateway 起動を行います。

## ドキュメント
- `docs/usage.md`: セットアップと運用手順
- `docs/specs.md`: 仕様の入口
- `docs/specs/`: 詳細仕様

## セットアップ
```powershell
uv sync --dev
uv run agent-port setup
```

`setup` は `.env.example` から `.env` を、`config/workspaces.json.example` から `config/workspaces.json` を作成します。既存の `.env` は secrets 保護のため上書きしません。`--force` を付けた場合でも、上書き対象は `config/workspaces.json` だけです。

workspace は必ず外部ディレクトリを指定してください。`agent-port` 本体 repo やその配下は workspace にできません。

## 確認
```powershell
uv run agent-port doctor
uv run agent-port config show
uv run agent-port workspace list
```

## 起動
```powershell
uv run agent-port gateway
```

`AGENT_PORT_DISCORD_TRIGGER_MODE=mention` のときは Bot 本体または Bot ロールへのメンション付きメッセージに反応します。`all` のときは通常メッセージにも反応します。

## テスト
```powershell
uv run pytest
```

## 主な設定
- `AGENT_PORT_WORKSPACE_REGISTRY=config/workspaces.json`
- `AGENT_PORT_DEFAULT_WORKSPACE=sample`
- `AGENT_PORT_DEFAULT_AGENT=codex`
- `AGENT_PORT_CODEX_COMMAND=codex`

後方互換のため `AGENT_PORT_CODEX_WORKSPACE` と `AGENT_PORT_AGENT_WORKSPACE` も読めますが、今後は workspace registry の利用を前提にしてください。
