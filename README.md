# agent-port

`agent-port` は、Discord などのチャットツールと Codex CLI などの Agent を中継する control plane です。本体 repo 自体は Agent の作業対象にせず、外部 workspace を `workspace_id` 経由で管理します。現在の最小実装は `Discord -> AgentRouter -> CodexRunner` です。

## ドキュメント
- `docs/usage.md`: セットアップと運用手順
- `docs/specs.md`: 仕様の入口
- `docs/specs/`: 詳細仕様

## セットアップ
```powershell
uv sync --dev
```

1. `.env.example` を参考に `.env` を作成します。
2. `config/workspaces.json.example` を参考に `config/workspaces.json` を作成します。
3. `config/workspaces.json` には、`agent-port` 本体の外にある workspace だけを登録します。

## 実行
```powershell
uv run python main.py
```

`AGENT_PORT_DISCORD_TRIGGER_MODE=mention` のときは Bot 本体または Bot ロールのメンション付きメッセージだけに反応します。`all` のときは通常メッセージにも反応します。返答方法は Agent が選び、通常返信かスレッド返信を切り替えます。

## テスト
```powershell
uv run pytest
```

## 現在の推奨設定
- `AGENT_PORT_WORKSPACE_REGISTRY=config/workspaces.json`
- `AGENT_PORT_DEFAULT_WORKSPACE=sample`
- `AGENT_PORT_DEFAULT_AGENT=codex`
- `AGENT_PORT_CODEX_COMMAND=codex`

`AGENT_PORT_CODEX_WORKSPACE` と `AGENT_PORT_AGENT_WORKSPACE` は後方互換用です。ただし、本体 repo やその配下を workspace にする指定は拒否します。
