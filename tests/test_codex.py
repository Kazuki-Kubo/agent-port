"""codex モジュールの振る舞いを検証する。"""

from pathlib import Path

import pytest

from agent_port import codex
from agent_port.codex import (
    CodexRunner,
    build_codex_exec_command,
    build_codex_prompt,
    resolve_command_path,
)
from agent_port.config import CodexConfig


def test_build_codex_exec_command_has_workspace_and_output() -> None:
    """実行コマンドに workspace と出力先が入ることを確認する。

    Returns
    -------
    None
        `codex exec` に必要な引数が組み立てられる。
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


def test_resolve_command_path_uses_windows_suffix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Windows の拡張子付きコマンドを見つけられることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        `shutil.which` を差し替える fixture。

    Returns
    -------
    None
        `codex.cmd` を実行パスとして解決できる。
    """

    def fake_which(command_name: str) -> str | None:
        """`which` の代替関数。

        Parameters
        ----------
        command_name : str
            探索対象のコマンド名。

        Returns
        -------
        str | None
            `codex.cmd` だけ見つける。
        """

        if command_name == "codex.cmd":
            return "C:/tools/codex.cmd"
        return None

    monkeypatch.setattr(codex.shutil, "which", fake_which)

    assert resolve_command_path("codex") == "C:/tools/codex.cmd"


def test_codex_runner_returns_backend_name() -> None:
    """runner が backend 名を返すことを確認する。

    Returns
    -------
    None
        backend 名は `codex` になる。
    """

    runner = CodexRunner(CodexConfig(name="codex", command="codex", timeout=300))

    assert runner.get_backend_name() == "codex"


def test_build_codex_prompt_trims_text() -> None:
    """prompt は前後の余分な空白だけを落とすことを確認する。

    Returns
    -------
    None
        delivery 制御を混ぜずに本文がそのまま使われる。
    """

    prompt = build_codex_prompt("  本文を返して  ")

    assert prompt == "本文を返して"
