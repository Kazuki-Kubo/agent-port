# Repository Guidelines

## Project Structure & Module Organization
主実装は `agent_port/` にあります。CLI は `agent_port/cli.py`、起動処理は `agent_port/app.py`、Discord 連携は `agent_port/discord_bot.py`、routing は `agent_port/router.py`、workspace 管理は `agent_port/workspaces.py` に集約しています。テストは `tests/`、使い方は `docs/usage.md`、仕様は `docs/specs.md` と `docs/specs/` に置きます。

## Build, Test, and Development Commands
- `uv sync --dev`: 開発依存を含めて環境を同期します。
- `uv run agent-port setup`: `.env` と `config/workspaces.json` の雛形を配置します。
- `uv run agent-port doctor`: 設定、workspace registry、Codex CLI を診断します。
- `uv run agent-port gateway`: Discord Gateway を起動します。
- `uv run pytest`: 全テストを実行します。

## Coding Style & Naming Conventions
Python 3.12 を前提にし、インデントは 4 スペースです。変数・関数は `snake_case`、クラスは `PascalCase`、定数は `UPPER_SNAKE_CASE` を使ってください。名前は意味が分かる範囲で短くし、重複した接頭辞や説明過多な識別子は避けます。クラス、関数、メソッド、テストには日本語の NumPy 形式 docstring を付けてください。

## Testing Guidelines
テストは `pytest` を使い、`tests/test_*.py` に配置します。新しい挙動を入れるときは、正常系と主な異常系を最低 1 件ずつ追加してください。CLI や設定変更では `uv run pytest` に加えて `uv run agent-port doctor` と `uv run agent-port config validate` で確認すると安全です。

## Commit & Pull Request Guidelines
コミットメッセージは `feat: ...`、`fix: ...`、`docs: ...` のような Conventional Commits を使います。区切りのよい単位で `git commit` し、共有が必要な変更は `git push` してください。PR では目的、主要変更、確認コマンド、Discord まわりの見た目変更があればその内容を簡潔に書きます。

## Documentation & Path Rules
ドキュメントは日本語で書き、パスはリポジトリ基準の相対パスを使います。使い方や仕様が大きくなったら `docs/usage/` や `docs/specs/` のように分割してください。`config/workspaces.json` の `path` は registry ファイル基準の相対パスまたは外部の絶対パスを使えますが、`agent-port` 本体やその配下は指定しません。
