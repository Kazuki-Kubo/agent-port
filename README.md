# agent-port

`agent-port` は、Discord などのチャットツールと Codex CLI などの Agent を中継する control plane です。最小構成では `Discord -> Router -> CodexRunner` を提供し、OpenClaw に近い流れで設定確認、workspace 管理、Gateway 起動を行います。

## ドキュメント
- `docs/usage.md`: セットアップ、Discord 側準備、起動、切り分け
- `docs/specs.md`: 仕様の入口
- `docs/specs/`: 詳細仕様

## 最短手順
```powershell
uv sync --dev
uv run agent-port setup
uv run agent-port doctor
uv run agent-port gateway
```

workspace は必ず外部ディレクトリを指定してください。`agent-port` 本体 repo やその配下は workspace にできません。

## 主な設定
- `AGENT_PORT_WORKSPACE_REGISTRY=config/workspaces.json`
- `AGENT_PORT_DEFAULT_WORKSPACE=sample`
- `AGENT_PORT_DEFAULT_AGENT=codex`
- `AGENT_PORT_CODEX_COMMAND=codex`
- `AGENT_PORT_DISCORD_TRIGGER_MODE=mention`

後方互換のため `AGENT_PORT_CODEX_WORKSPACE` と `AGENT_PORT_AGENT_WORKSPACE` も読めますが、今後は workspace registry の利用を前提にしてください。

## テスト
```powershell
uv run pytest
```
