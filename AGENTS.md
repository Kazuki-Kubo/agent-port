# Repository Guidelines

## Project Structure & Module Organization
実装本体は `agent_port/` に置きます。`main.py` は薄い起動口だけにし、機能は `agent_port/` 配下へ寄せます。テストは `tests/`、使い方は `docs/usage.md`、仕様は `docs/specs.md` と `docs/specs/` にまとめます。ドキュメント名は簡潔で分かりやすくし、内容が大きくなったら `docs/usage/` や `docs/specs/` のように分割します。

## Build, Test, and Development Commands
- `uv sync --dev`: 開発依存を含めて同期します。
- `uv run python main.py`: Bot を起動します。
- `uv run pytest`: テストを実行します。

設定は `.env` から読みます。.env の共有は禁止し、例は `.env.example` にだけ置きます。

## Coding Style & Naming Conventions
Python 3.12 を前提にします。インデントは 4 スペース、関数と変数は `snake_case`、クラスは `PascalCase`、定数は `UPPER_SNAKE_CASE` を使います。全てのクラス・関数・メソッド・テストには、日本語の NumPy 形式 docstring を付けてください。

## Testing Guidelines
テストは `pytest` を使い、`tests/test_*.py` に追加します。機能追加時は正常系と主な異常系を最低 1 件ずつ入れてください。外部サービス依存はモック化し、ローカルで `uv run pytest` が通る状態を維持します。

## Commit & Pull Request Guidelines
コミットメッセージは `feat: ...`、`fix: ...`、`docs: ...` のような Conventional Commits 形式を使います。区切りのよい単位で `git commit` し、共有が必要な変更は `git push` します。PR には目的、主要変更、テスト結果、必要なら設定変更やスクリーンショットを含めてください。

## Documentation & Path Rules
ドキュメントには使い方と仕様を保存します。パスはフォルダ移動に耐えられるよう、常にリポジトリ基準の相対パスで記述してください。新しい設定項目や制約を追加したら、コード変更と同じタイミングで `docs/usage.md` と `docs/specs/` を更新します。
