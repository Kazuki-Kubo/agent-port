# agent-port

`agent-port` は、Discord などのチャットツールと Codex CLI などの Agent を中継するソフトウェアです。現時点の最小実装は `Discord -> AgentRouter -> Codex CLI` で動作します。将来的にチャットツールや Agent を増やせるよう、内部は adapter と router を前提に整理しています。

## ドキュメント
- `docs/usage.md`: セットアップと実行手順
- `docs/specs.md`: 仕様の入口
- `docs/specs/`: 詳細仕様

ドキュメント内のパスは、移動しやすさを優先してリポジトリ基準の相対パスで記述します。使い方や仕様が大きくなった場合は、`docs/usage/` や `docs/specs/` のようにフォルダへ分割します。

## セットアップ
```powershell
uv sync --dev
```

`.env.example` を参考に `.env` を作成します。秘密値は `.env` に置き、共有時は `.env.example` だけを使います。

## 実行
```powershell
uv run python main.py
```

`AGENT_PORT_DISCORD_TRIGGER_MODE=mention` のときは Bot 本体または Bot ロールのメンション付きメッセージに反応します。`all` のときは通常メッセージにも反応します。

Agent の返答は、先頭制御行で `reply` と `thread` を選べます。現在の Codex 実装では、短い単発回答は通常返信、長い説明や継続作業はスレッド返信を選ぶよう指示しています。

## テスト
```powershell
uv run pytest
```

## 現在の推奨環境変数
- `AGENT_PORT_CHAT_BACKEND=discord`
- `AGENT_PORT_DEFAULT_AGENT=codex`
- `AGENT_PORT_CODEX_WORKSPACE=.` または絶対パス
- `AGENT_PORT_CODEX_COMMAND=codex`

`AGENT_PORT_AGENT_BACKEND` と `AGENT_PORT_AGENT_WORKSPACE` は後方互換として読み取りますが、新規設定では使わない方針です。
