# 使い方

## 前提
このリポジトリでは `uv` を使います。あわせて、次が使える状態にしてください。

- Discord Bot token
- Discord サーバーへ追加済みの Bot
- ローカルで実行できる `codex` コマンド
- `agent-port` 本体とは別の外部 workspace

## 初期セットアップ
依存を入れて、設定ファイルの雛形を作ります。

```powershell
uv sync --dev
uv run agent-port setup
```

生成されるファイルは次の 2 つです。

- `.env`
- `config/workspaces.json`

既存の `.env` は secrets 保護のため上書きしません。`uv run agent-port setup --force` を付けても、上書き対象は `config/workspaces.json` だけです。

## Discord 側の準備
Discord Developer Portal で対象アプリを開き、次を確認してください。

1. Bot を作成して token を取得する
2. `MESSAGE CONTENT INTENT` を有効にする
3. Bot を対象サーバーに招待する

`AGENT_PORT_DISCORD_APPLICATION_ID` はアプリケーション ID です。今の最小実装では必須ではありませんが、将来の拡張を考えて設定しておくと扱いやすいです。

## `.env` の設定
最小構成の例です。

```env
AGENT_PORT_CHAT_BACKEND=discord
AGENT_PORT_DISCORD_BOT_TOKEN=your-discord-bot-token
AGENT_PORT_DISCORD_APPLICATION_ID=your-discord-application-id
AGENT_PORT_DISCORD_TRIGGER_MODE=mention
AGENT_PORT_WORKSPACE_REGISTRY=config/workspaces.json
AGENT_PORT_DEFAULT_WORKSPACE=sample
AGENT_PORT_DEFAULT_AGENT=codex
AGENT_PORT_CODEX_COMMAND=codex
AGENT_PORT_CODEX_TIMEOUT_SECONDS=300
AGENT_PORT_LOG_LEVEL=INFO
```

主な値の意味は次の通りです。

- `AGENT_PORT_DISCORD_TRIGGER_MODE=mention`
  Bot 本体または Bot ロールへのメンション付きメッセージだけ処理します。
- `AGENT_PORT_DISCORD_TRIGGER_MODE=all`
  通常メッセージも処理します。誤反応しやすいので運用には注意してください。
- `AGENT_PORT_DEFAULT_WORKSPACE`
  `config/workspaces.json` に定義した workspace ID を指定します。

## `config/workspaces.json` の設定
workspace は `agent-port` 本体 repo の外に置いてください。`path` は `config/workspaces.json` 基準の相対パス、または外部の絶対パスで指定できます。

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

各キーの意味は次の通りです。

- `id`: Discord 側から参照する workspace ID
- `path`: 実際に Codex を動かすディレクトリ
- `allowed_agents`: この workspace で許可する agent 一覧
- `description`: 補足説明

## 設定確認
起動前に次を実行してください。

```powershell
uv run agent-port doctor
uv run agent-port config validate
uv run agent-port workspace list
```

確認ポイントは次です。

- `doctor` で `ok`
- `default_workspace=...` が意図した値
- `codex_found=True`
- `workspace list` に対象 workspace が出る

## 起動
```powershell
uv run agent-port gateway
```

起動後はログに `agent-port is ready.` と `Discord Bot connected ...` が出れば接続完了です。

## Discord からの使い方
`mention` モードなら、Bot 本体または Bot ロールをメンションして送ります。

```text
@Bot この workspace を見て
```

`all` モードなら通常メッセージも処理します。

Codex の返答 1 行目に `[delivery:reply]` または `[delivery:thread]` がある場合、`agent-port` はその指定に従って通常返信またはスレッド返信を選びます。

## トラブル時の確認順
返答が来ないときは次の順で切り分けます。

1. `uv run agent-port doctor` で設定エラーがないか確認する
2. Discord Developer Portal で `MESSAGE CONTENT INTENT` が有効か確認する
3. `workspace list` で対象 workspace が出ているか確認する
4. `codex` コマンドが単体で実行できるか確認する
5. 起動ログに `Received Discord message` が出ているか確認する
6. その後に `Starting Codex command` が出て止まるなら Agent 側の処理を疑う

## テスト
```powershell
uv run pytest
```
