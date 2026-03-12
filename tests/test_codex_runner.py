"""codex_runner モジュールの動作を検証するテスト。"""

from pathlib import Path

import pytest

from agent_port import codex_runner
from agent_port.codex_runner import (
    CodexRunner,
    build_codex_exec_command,
    build_codex_prompt,
    resolve_command_path,
)
from agent_port.config import CodexAgentConfig


def test_build_codex_exec_command_includes_workspace_and_output() -> None:
    """Codex 実行コマンドに必要な引数が含まれることを検証する。

    Returns
    -------
    None
        workspace、出力ファイル、prompt が正しく組み立てられることを確認する。
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
    """`which` が空でも `.cmd` 拡張子で解決できることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        `shutil.which` を差し替えるための fixture。

    Returns
    -------
    None
        Windows 向けフォールバックが機能することを確認する。
    """

    def fake_which(command_name: str) -> str | None:
        """テスト用の疑似 which 実装を返す。

        Parameters
        ----------
        command_name : str
            解決対象のコマンド名。

        Returns
        -------
        str | None
            `codex.cmd` にだけパスを返し、それ以外は `None` を返す。
        """

        if command_name == "codex.cmd":
            return "C:/tools/codex.cmd"
        return None

    monkeypatch.setattr(codex_runner.shutil, "which", fake_which)

    assert resolve_command_path("codex") == "C:/tools/codex.cmd"


def test_codex_runner_returns_backend_name() -> None:
    """CodexRunner が自身の backend 名を返すことを検証する。

    Returns
    -------
    None
        registry 登録用の backend 名が `codex` であることを確認する。
    """

    runner = CodexRunner(
        CodexAgentConfig(
            backend_name="codex",
            workspace=Path(".").resolve(),
            command="codex",
            timeout_seconds=300,
        )
    )

    assert runner.get_backend_name() == "codex"


def test_build_codex_prompt_includes_delivery_instruction() -> None:
    """Codex prompt に配送モード指示を含めることを検証する。

    Returns
    -------
    None
        Agent が reply と thread を選べる指示が先頭へ追加されることを確認する。
    """

    prompt = build_codex_prompt("実装内容を説明して")

    assert "[delivery:reply]" in prompt
    assert "[delivery:thread]" in prompt
    assert prompt.rstrip().endswith("実装内容を説明して")
