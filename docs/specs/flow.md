# 処理フロー

## 基本フロー
1. Chat Adapter がチャットメッセージを受け取る
2. Chat Adapter が trigger 条件に一致する本文だけを取り出して Core に渡す
3. Core が backend と workspace を決定する
4. Core が解決済み workspace を付けて Agent Adapter を実行する
5. Agent Adapter が Agent を実行し、返答本文を返す
6. Chat Adapter が返答をチャットツールへ送る

## 内部イベント
最小実装では明示的なイベントバスはまだ持たず、次の段階で整理します。
- `message_received`
- `agent_started`
- `agent_finished`
- `agent_failed`

## エラー処理
- チャット受信条件を満たさない場合は何も返さない
- Agent 実行に失敗した場合は、チャット側へエラーを返す
- スレッド返信に失敗した場合は通常返信へフォールバックする

## session と会話
最小実装では、Discord の 1 メッセージを 1 回の Agent 実行として扱います。今後は `channel/thread -> session` の対応を Core で保持し、会話ごとの agent 切替や `workspace_id` の保持を追加します。

## 返信形式
Agent は返答 1 行目に次のどちらかを返します。
- `[delivery:reply]`
- `[delivery:thread]`

Chat Adapter はこの制御行を読み、通常返信またはスレッド返信を選びます。
