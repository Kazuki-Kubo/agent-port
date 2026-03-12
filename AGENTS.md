# Repository Guidelines

## Project Structure & Module Organization
実装本体は `agent_port/` にあります。CLI は `agent_port/cli.py`、起動処理は `agent_port/app.py`、Discord 側の中継は `agent_port/discord_bridge.py`、workspace 管理は `agent_port/workspace_registry.py` に置いています。テストは `tests/`、利用手順は `docs/usage.md`、仕様は `docs/specs.md` と `docs/specs/` にまとめます。workspace 実体はこの repo の外で管理し、`config/workspaces.json` で参照します。

## Build, Test, and Development Commands
- `uv sync --dev`: 開発依存を含めて環境を同期します。
- `uv run agent-port setup`: `.env` と `config/workspaces.json` の雛形を配置します。
- `uv run agent-port doctor`: 設定、workspace registry、Codex CLI を診断します。
- `uv run agent-port gateway`: Gateway を前面起動します。
- `uv run pytest`: テストを実行します。

## Coding Style & Naming Conventions
Python 3.12 を前提にし、インデントは 4 スペースです。関数・変数は `snake_case`、クラスは `PascalCase`、定数は `UPPER_SNAKE_CASE` を使ってください。全クラス・関数・メソッド・テストには日本語の NumPy 形式 docstring を付けます。責務が増えたら `agent_port/` 配下で小さなモジュールに分割してください。

## Testing Guidelines
テストは `pytest` を使い、`tests/test_*.py` に追加します。新しいコマンドや分岐を増やしたら、正常系と主要な異常系を最低 1 件ずつ入れてください。CLI 変更時は `uv run pytest` に加えて `uv run agent-port doctor` や `uv run agent-port config validate` の実行結果も確認します。

## Commit & Pull Request Guidelines
コミットメッセージは `feat: ...`、`fix: ...`、`docs: ...` のような Conventional Commits を使います。区切りのよい単位で `git commit` し、共有が必要な変更は `git push` してください。PR では目的、主な変更、確認コマンド、必要なら Discord 側の操作手順を簡潔に書きます。

## Documentation & Path Rules
ドキュメントは日本語で書き、リポジトリ基準の相対パスを使います。使い方と仕様が大きくなったら `docs/usage/` と `docs/specs/` のように分割してください。`config/workspaces.json` の `path` は registry ファイル基準の相対パスまたは絶対パスを許可しますが、`agent-port` 本体やその配下は workspace にしてはいけません。
