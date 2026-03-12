# 全体像

## 目的
このソフトウェアの第一目標は、Discord と Codex CLI を中継し、Discord を Codex の UI として使えるようにすることです。

## 責務
このソフトウェアは、チャットツールから Agent への入力と、Agent からチャットツールへの出力を中継する control plane です。
- Discord 側のイベントを受ける
- Agent 側へ prompt を渡す
- Agent の返答を Discord 側へ返す

## 長期方針
- チャットツール側は Discord から他サービスへ拡張できる構造にする
- Agent 側は Codex CLI から他の AI Agent へ拡張できる構造にする
- 中核ロジックはチャット層と Agent 層から分離する

## 非目標
- 初期段階で複数チャットツールを同時実装すること
- 初期段階で複数 Agent を同時実装すること
- `agent-port` 本体 repo を Agent workspace にすること

## 初期スコープ
- チャットツールは Discord のみ
- Agent は Codex CLI のみ
- 外部 workspace を `workspace_id` で指定する
- 1 つの Discord メッセージを 1 回の Agent 実行へ中継する
