"""codex_runner モジュールの振る舞いを検証するテスト。"""

from pathlib import Path

import pytest

from agent_port import codex_runner
from agent_port.codex_runner import build_codex_exec_command, resolve_command_path


def test_build_codex_exec_command_includes_workspace_and_output() -> None:
    """Codex 実行コマンドに必要な引数が含まれることを確認する。

    Returns
    -------
    None
        workspace、出力ファイル、プロンプトが順序どおり含まれることを検証する。
    """

    workspace = Path("workspace").resolve()
    output_path = Path("output.txt").resolve()

    command = build_codex_exec_command(
        codex_command="codex",
        workspace=workspace,
        prompt="say hello",
        output_path=output_path,
    )

    assert command[:3] == ["codex", "exec", "--skip-git-repo-check"]
    assert "-C" in command
    assert str(workspace) in command
    assert "-o" in command
    assert str(output_path) in command
    assert command[-1] == "say hello"


def test_resolve_command_path_uses_windows_fallback_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """コマンド名のみ指定された場合でも `.cmd` 形式へ解決できることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        `shutil.which` の戻り値を差し替えるためのフィクスチャ。

    Returns
    -------
    None
        `.cmd` へのフォールバックが機能することを検証する。
    """

    def fake_which(command_name: str) -> str | None:
        """指定されたコマンド名に応じて疑似的な探索結果を返す。

        Parameters
        ----------
        command_name : str
            探索対象のコマンド名。

        Returns
        -------
        str | None
            `.cmd` だけ存在する状況を模した探索結果。
        """

        if command_name == "codex.cmd":
            return "C:/tools/codex.cmd"
        return None

    monkeypatch.setattr(codex_runner.shutil, "which", fake_which)

    assert resolve_command_path("codex") == "C:/tools/codex.cmd"
