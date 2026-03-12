# 処理フロー

## 基本フロー
1. Chat Adapter がチャットメッセージを受け取る。
2. Chat Adapter が trigger 条件に一致する本文だけを取り出して Core に渡す。
3. Core が `agent_id` と `workspace_id` を決める。
4. Core が解決済み workspace を付けて Agent Adapter を実行する。
5. Agent Adapter が Agent を実行し、本文中心の結果を返す。
6. Chat Adapter が配送先と配送方法を決めてチャットへ返す。

## イベント
最小構成では次の内部イベントを想定する。

- `message_received`
- `agent_started`
- `agent_finished`
- `agent_failed`

## エラー時の扱い
- trigger 条件に合わないメッセージは無視する。
- workspace または agent の組み合わせが不正なら host 側でエラーを返す。
- Agent 実行失敗時はチャット側に要約エラーを返す。
- thread 返信が使えない環境では通常返信へフォールバックできる形を保つ。

## session と会話
最小構成では `channel/thread -> session` を基本に扱う。今後はこの session に対して `agent_id` と `workspace_id` の binding を持たせる。

## 配送方法
OpenClaw に寄せて、配送方法は host 側が決める。Agent は本文を返すことを優先し、Discord Adapter が次を選ぶ。

- 通常チャンネル: `reply`
- 既存スレッド: `thread`

将来的に `AgentRunResult.delivery_mode` を使う場合も、最終決定権は Chat Adapter 側に置く。
