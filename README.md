# agent-port

`agent-port` は、チャットツールと AI Agent を仲介するソフトウェアです。第一段階では Discord と Codex CLI を接続し、Discord を Codex の UI として使うことを目指します。開発環境の管理と実行には `uv` を使います。

## ドキュメント
ドキュメントは `docs/` 配下で管理し、次の 2 種類を保存します。

- `docs/usage.md`: 使い方、実行手順、運用手順
- `docs/specs.md`: 仕様の入口
- `docs/specs/`: 詳細仕様

ファイル名は簡潔で分かりやすいものを使ってください。パスはフォルダを移動しやすいように、常にリポジトリ基準の相対パスで記載してください。使い方や仕様が大きくなった場合は、`docs/usage/` や `docs/specs/` のようにフォルダへ分割してください。

## セットアップ
```powershell
uv sync --dev
```

## 実行
```powershell
uv run python main.py
```

## テスト
```powershell
uv run pytest
```

## 開発メモ
- Python バージョンは 3.12 です。
- 関数、クラス、メソッド、テストには日本語の NumPy 形式 docstring を付けます。
- 詳細な運用ルールは `AGENTS.md` を参照してください。
