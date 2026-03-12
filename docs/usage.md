# 使い方

## 前提
このリポジトリは `uv` で動かします。あわせて次を用意してください。

- Discord Bot token
- Bot を追加した Discord サーバー
- ローカルで実行できる `codex` コマンド
- `agent-port` 本体とは別の外部 workspace

## 初期セットアップ
依存関係を入れたうえで、設定ファイルの雛形を生成します。

```powershell
uv sync --dev
uv run agent-port setup
```

生成対象は次です。

- `.env`
- `config/workspaces.json`

`.env` は秘密情報を含むため、内容をそのまま表示しないでください。`setup --force` を使っても既存の `.env` は上書きしません。

## Discord 側の準備
Discord Developer Portal で対象アプリを設定します。

1. Bot を作成して token を取得する
2. `MESSAGE CONTENT INTENT` を有効にする
3. Bot を対象サーバーへ招待する

`AGENT_PORT_DISCORD_APPLICATION_ID` は将来の連携用です。現在の最小実装では未使用ですが、値を入れておいて問題ありません。

## `.env` の例
`.env.example` を元に、実値を入れます。

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

主要な設定:

- `AGENT_PORT_DISCORD_TRIGGER_MODE=mention`
  Bot 本体または Bot role へのメンションがあるメッセージだけを処理します。
- `AGENT_PORT_DISCORD_TRIGGER_MODE=all`
  通常メッセージも処理します。公開サーバーでは誤反応に注意してください。
- `AGENT_PORT_DEFAULT_WORKSPACE`
  `config/workspaces.json` に定義した workspace ID を指定します。

## `config/workspaces.json` の例
workspace は `agent-port` 本体の外側に置きます。`path` は `config/workspaces.json` 基準の相対パスでも、絶対パスでも構いません。

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

各キー:

- `id`: Discord 側から参照する短い識別子
- `path`: Agent が実際に作業する外部ディレクトリ
- `allowed_agents`: その workspace で使える agent 一覧
- `description`: 補足説明

## 起動前チェック
設定が正しいかは次で確認します。

```powershell
uv run agent-port doctor
uv run agent-port config validate
uv run agent-port workspace list
```

確認したい点:

- `doctor` が `ok` になる
- `default_workspace=...` が期待どおり
- `codex_found=True`
- `workspace list` に対象 workspace が出る

## 起動
Gateway を起動します。

```powershell
uv run agent-port gateway
```

ログに `agent-port is ready.` と `Discord Bot connected ...` が出れば待受状態です。

## Discord からの使い方
`mention` モードなら、Bot 本体または Bot role を含めて送ります。

```text
@Bot この workspace を見て
```

`all` モードなら通常メッセージでも処理します。

配送方法は Agent ではなく host 側が決めます。

- 通常チャンネルで受けたメッセージ: 元メッセージへの `reply`
- 既存スレッドで受けたメッセージ: そのスレッドへ送信

## 返答が来ないとき
次の順で切り分けます。

1. `uv run agent-port doctor` で設定エラーがないか確認する
2. Discord Developer Portal で `MESSAGE CONTENT INTENT` が有効か確認する
3. `uv run agent-port workspace list` で workspace が読めているか確認する
4. `codex` コマンドがローカルで実行できるか確認する
5. 起動ログに `Received Discord message` が出ているか確認する
6. その後に `Starting Codex command` が出るか確認する

`AGENT_PORT_LOG_LEVEL=DEBUG` にすると、Codex の生出力もログに出ます。秘密情報が混ざる可能性があるため、共有時は注意してください。

## テスト
```powershell
uv run pytest
```
