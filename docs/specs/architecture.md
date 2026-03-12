# アーキテクチャ

## 層構造
システムは次の 3 層で構成します。
- Chat Adapter 層: Discord などのチャットツールとの入出力を扱う
- Core 層: trigger 判定、routing、workspace 解決を扱う
- Agent Adapter 層: Codex CLI などの Agent 実行を扱う

現在の最小実装は `DiscordBot -> Router -> CodexRunner` です。

## control plane と workspace
`agent-port` 本体 repo は control plane です。Agent の作業対象は外部 workspace とし、`config/workspaces.json` で管理します。

Core は `workspace_id` を受け取り、`Workspaces` から実 path を解決して Agent へ渡します。これにより、チャット層や Agent 実装が本体 repo の path を直接扱わずに済みます。

## routing
Core は単一 Agent を直呼びしません。`AgentStore` に backend を登録し、`Router` が既定 backend または明示 backend を選びます。同時に `Workspaces` から既定 workspace または明示 workspace を選び、`backend + workspace_id` の組み合わせを確定します。

## workspace registry
workspace は `config/workspaces.json` で定義します。各項目は次のキーを持ちます。
- `id`: workspace ID
- `path`: 実際の workspace path
- `allowed_agents`: 利用を許可する agent backend 一覧
- `description`: 補足説明

`path` は registry ファイル基準の相対パスまたは外部の絶対パスを許可します。`agent-port` 本体ディレクトリとその配下は拒否します。

## 環境変数
- `AGENT_PORT_WORKSPACE_REGISTRY`: workspace registry JSON
- `AGENT_PORT_DEFAULT_WORKSPACE`: 既定 workspace ID
- `AGENT_PORT_DEFAULT_AGENT`: 既定 agent backend。現在は `codex`
- `AGENT_PORT_DISCORD_BOT_TOKEN`: Discord Bot token
- `AGENT_PORT_DISCORD_APPLICATION_ID`: Discord application ID
- `AGENT_PORT_DISCORD_TRIGGER_MODE`: `mention` または `all`
- `AGENT_PORT_CODEX_COMMAND`: Codex CLI コマンド
- `AGENT_PORT_CODEX_TIMEOUT_SECONDS`: Codex timeout
- `AGENT_PORT_LOG_LEVEL`: ログレベル

旧環境変数 `AGENT_PORT_CODEX_WORKSPACE` と `AGENT_PORT_AGENT_WORKSPACE` は後方互換としてのみ読み込みます。
