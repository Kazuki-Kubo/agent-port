# アーキテクチャ

## 層構成
システムは次の 3 層で構成します。

- Chat Adapter 層: Discord など外部チャットツールとの入出力を担当
- Core 層: trigger 判定、routing、workspace 解決、session 管理を担当
- Agent Adapter 層: Codex CLI や将来の Claude Code など個別 Agent 実装を担当

現在の最小実装は `DiscordAgentBridgeClient -> AgentRouter -> CodexRunner` です。

## control plane と workspace の分離
`agent-port` 本体 repo は control plane です。Agent の作業対象にしてはいけません。作業対象は `config/workspaces.json` に登録した外部 workspace だけです。

Core は `workspace_id` を受け取り、`WorkspaceRegistry` から実 path を解決して Agent へ渡します。これにより、チャット層や Agent 実装が本体 repo のパスを直接扱わずに済みます。

## routing
Core では単一 Agent を直呼びしません。`AgentRegistry` に複数 backend を登録し、`AgentRouter` が既定 backend または明示 backend を選びます。同時に `WorkspaceRegistry` から既定 workspace または明示 workspace を選び、`backend + workspace_id` の組み合わせを確定します。

## workspace registry
workspace は `config/workspaces.json` で管理します。各定義は次の要素を持ちます。

- `id`: workspace ID
- `path`: 実際の workspace path
- `allowed_agents`: 利用を許可する agent backend 一覧
- `description`: 用途説明

`path` は registry ファイル基準の相対パスか絶対パスを許可します。ただし、`agent-port` 本体ディレクトリとその配下は拒否します。

## 環境変数
- `AGENT_PORT_WORKSPACE_REGISTRY`: workspace registry JSON パス
- `AGENT_PORT_DEFAULT_WORKSPACE`: 既定 workspace ID
- `AGENT_PORT_DEFAULT_AGENT`: 既定 agent backend。現在は `codex`
- `AGENT_PORT_DISCORD_BOT_TOKEN`: Discord Bot token
- `AGENT_PORT_DISCORD_APPLICATION_ID`: Discord application ID
- `AGENT_PORT_DISCORD_TRIGGER_MODE`: `mention` または `all`
- `AGENT_PORT_CODEX_COMMAND`: Codex CLI コマンド
- `AGENT_PORT_CODEX_TIMEOUT_SECONDS`: Codex timeout
- `AGENT_PORT_LOG_LEVEL`: ログレベル

旧環境変数 `AGENT_PORT_CODEX_WORKSPACE` と `AGENT_PORT_AGENT_WORKSPACE` は後方互換でのみ読み取ります。
