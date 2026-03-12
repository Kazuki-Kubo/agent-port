# アーキテクチャ

## 論理構成
システムは次の 3 層で構成します。

- Chat Adapter 層: Discord などの外部チャット API と接続する
- Core 層: 正規化、ルーティング、セッション管理、状態管理を行う
- Agent Adapter 層: Codex CLI などの Agent と接続する

## 主要コンポーネント
### Chat Adapter
責務は、チャット固有のイベントを内部イベントへ変換し、内部イベントからチャット固有の送信処理へ戻すことです。

最低限、次の操作を提供します。

- メッセージ受信
- メッセージ送信
- 途中経過の更新
- エラー通知
- 将来拡張として、スレッド作成、添付送信、入力中表示

### Core
責務は、システムの中立的な業務ロジックを集約することです。

Core は少なくとも次を持ちます。

- `MessageRouter`: 受信イベントの振り分け
- `SessionStore`: 会話単位の状態管理
- `AgentDispatcher`: Agent Adapter の起動と応答購読
- `EventNormalizer`: チャットと Agent のイベントを共通形式へ変換
- `ResponseFormatter`: Agent 出力をチャット向けに整形

### Agent Adapter
責務は、Agent 固有の入出力を共通インターフェースへ合わせることです。

最低限、次の操作を提供します。

- セッション開始または再利用
- ユーザーメッセージ送信
- ストリーム応答受信
- 実行中断
- 実行状態取得

## 内部モデル
中核では、実装依存を減らすために次の概念を共通モデルとして持ちます。

- `Conversation`: チャット側の会話単位
- `Session`: Agent 側の継続実行単位
- `Message`: 送受信テキスト
- `Attachment`: 将来対応するファイル情報
- `Run`: 1 回の Agent 実行
- `Event`: システム内部で流れる正規化済みイベント

## 推奨インターフェース
実装言語に依存しない最小契約として、次の責務を持つインターフェースを定義します。

### Chat Adapter 契約
- 受信イベントを `Event` に変換して Core へ渡す
- `Conversation` を指定してメッセージを送信する
- 既存メッセージを更新する
- エラー通知を送信する

### Agent Adapter 契約
- `Session` と入力メッセージを受け取り、`Run` を開始する
- 実行中の出力を `Event` として順次返す
- `Run` を中断する
- `Session` の再利用可否を返す

### Core 契約
- 受信 `Event` を解釈し、処理対象の `Conversation` と `Session` を決定する
- Chat Adapter と Agent Adapter の差異を吸収する
- 実行中状態、失敗状態、完了状態を一貫した内部イベントとして扱う

## セッション対応付け
初期仕様では、1 つのチャット会話に 1 つの Agent セッションを対応付けます。

- Discord のチャンネルまたはスレッドを `Conversation` とみなす
- `Conversation` ごとに `Session` を 1 つ保持する
- 明示的なリセットがあるまで同じ `Session` を再利用する

## 拡張ポイント
### チャット側
新しいチャットツールを追加するときは、Core を変更せず、新しい Chat Adapter を追加できることを目標にします。

### Agent 側
新しい Agent を追加するときは、Core を変更せず、新しい Agent Adapter を追加できることを目標にします。

### 設定
実行時に使用する Chat Adapter と Agent Adapter は設定で選択できるようにします。

初期仕様では、少なくとも次の設定項目を持ちます。

- `chat_backend`: 利用するチャット実装の識別子。例: `discord`
- `agent_backend`: 利用する Agent 実装の識別子。例: `codex`
- `session_store`: セッション保存方式の識別子。初期値はメモリ上の保存
- `log_level`: ログ出力レベル

## 初期実装方針
初期実装では単一プロセス構成とし、Core が Chat Adapter と Agent Adapter を直接呼び出します。将来はキューやワーカーを挟めるように、Core の入出力形式はできるだけ純粋なデータ構造で保ちます。
