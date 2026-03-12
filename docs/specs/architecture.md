# アーキテクチャ

## 層構成
システムは次の 3 層で構成します。

- Chat Adapter 層: Discord など外部チャットツールとの入出力を担当
- Core 層: trigger 判定、routing、session 管理、応答整形を担当
- Agent Adapter 層: Codex CLI や将来の Claude Code など個別 Agent 実装を担当

現在の最小実装は `DiscordAgentBridgeClient -> AgentRouter -> CodexRunner` です。

## マルチエージェント方針
Core では単一 Agent を直呼びしません。`AgentRegistry` に複数 backend を登録し、`AgentRouter` が既定 backend または明示指定 backend を選びます。これにより、初期実装は Codex のみでも、将来 `claude_code` などを追加できます。

Agent 実装は共通インターフェース `AgentRunner` に従います。入力は `AgentRequest`、出力は `AgentRunResult` で統一します。Chat Adapter は個別 Agent の詳細を知らず、Core 経由で呼び出します。

## workspace
workspace は Agent ごとに持ちます。現在は `CodexAgentConfig.workspace` を使い、`AGENT_PORT_CODEX_WORKSPACE` から読み込みます。相対パスと絶対パスの両方を許可し、相対パスは設定基準ディレクトリから解決します。

## 環境変数
- `AGENT_PORT_CHAT_BACKEND`: 現在は `discord`
- `AGENT_PORT_DEFAULT_AGENT`: 既定 Agent backend 名。現在は `codex`
- `AGENT_PORT_DISCORD_BOT_TOKEN`: Discord Bot トークン
- `AGENT_PORT_DISCORD_APPLICATION_ID`: Discord アプリケーション ID
- `AGENT_PORT_DISCORD_TRIGGER_MODE`: `mention` または `all`
- `AGENT_PORT_CODEX_WORKSPACE`: Codex 用 workspace
- `AGENT_PORT_CODEX_COMMAND`: Codex CLI コマンド
- `AGENT_PORT_CODEX_TIMEOUT_SECONDS`: Codex 実行タイムアウト
- `AGENT_PORT_LOG_LEVEL`: ログレベル

旧環境変数 `AGENT_PORT_AGENT_BACKEND` と `AGENT_PORT_AGENT_WORKSPACE` は後方互換でのみ読み取ります。
