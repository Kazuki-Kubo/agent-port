"""Codex CLI を呼び出す Agent 実装。"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import shutil
import tempfile

from agent_port.agents import AgentRequest, AgentRunResult, AgentRunner
from agent_port.config import CodexAgentConfig

CODEX_DELIVERY_INSTRUCTION = """あなたは Discord 上で動く Agent です。

出力ルール:
- 1 行目には必ず `[delivery:reply]` または `[delivery:thread]` を書いてください。
- 2 行目以降に、Discord へそのまま送る日本語の本文だけを書いてください。
- 制御行を本文に繰り返さないでください。
- 短い単発回答は `reply` を選んでください。
- 複数ステップの調査、実装、レビュー、長い説明は `thread` を選んでください。

ユーザー入力:
"""


class CodexExecutionError(RuntimeError):
    """Codex CLI の実行に失敗した場合の例外。"""


CodexRunResult = AgentRunResult


class CodexRunner(AgentRunner):
    """Codex CLI を実行して最終応答を抽出する。"""

    def __init__(self, config: CodexAgentConfig) -> None:
        """Codex 実行設定を保持する。

        Parameters
        ----------
        config : CodexAgentConfig
            Codex backend 用の設定。

        Returns
        -------
        None
            Codex 実行時に利用する設定を保存する。
        """

        self._config = config
        self._logger = logging.getLogger(__name__)

    def get_backend_name(self) -> str:
        """backend 名を返す。

        Returns
        -------
        str
            この実装が扱う backend 名。
        """

        return self._config.backend_name

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """Codex を AgentRunner として実行する。

        Parameters
        ----------
        request : AgentRequest
            Codex に渡す prompt を持つ要求。

        Returns
        -------
        AgentRunResult
            Codex から抽出した最終メッセージ。
        """

        return await self.run_prompt(request.prompt)

    async def run_prompt(self, prompt: str) -> CodexRunResult:
        """workspace を指定して Codex CLI を実行する。

        Parameters
        ----------
        prompt : str
            Codex に渡すユーザー入力。

        Returns
        -------
        CodexRunResult
            最終メッセージと生出力。

        Raises
        ------
        CodexExecutionError
            実行失敗、タイムアウト、空応答などの場合。
        """

        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise CodexExecutionError("Codex に渡す prompt が空です。")

        output_path = _create_output_path()
        command = build_codex_exec_command(
            codex_command=resolve_command_path(self._config.command),
            workspace=self._config.workspace,
            prompt=build_codex_prompt(normalized_prompt),
            output_path=output_path,
        )
        process: asyncio.subprocess.Process | None = None
        stdout_bytes = b""
        self._logger.info(
            "Starting Codex command workspace=%s timeout_seconds=%s prompt_length=%s",
            self._config.workspace,
            self._config.timeout_seconds,
            len(normalized_prompt),
        )

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout_bytes, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self._config.timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise CodexExecutionError(
                f"Codex CLI コマンドが見つかりません: {self._config.command}"
            ) from exc
        except TimeoutError as exc:
            if process is not None:
                process.kill()
                await process.communicate()
            raise CodexExecutionError("Codex CLI の実行がタイムアウトしました。") from exc
        finally:
            raw_message = _read_output_file(output_path)
            _remove_output_file(output_path)

        raw_output = stdout_bytes.decode("utf-8", errors="replace")
        if process is None:
            raise CodexExecutionError("Codex CLI プロセスを起動できませんでした。")

        if process.returncode != 0:
            raise CodexExecutionError(
                "Codex CLI の実行に失敗しました。\n"
                f"returncode={process.returncode}\n"
                f"{raw_output.strip()}"
            )

        final_message = _extract_last_message(raw_message)
        if not final_message:
            raise CodexExecutionError(
                "Codex CLI から最終メッセージを抽出できませんでした。"
            )

        self._logger.info(
            "Codex command completed returncode=%s response_length=%s",
            process.returncode,
            len(final_message),
        )
        return AgentRunResult(
            backend_name=self.get_backend_name(),
            message=final_message,
            raw_output=raw_output,
        )


def build_codex_exec_command(
    codex_command: str,
    workspace: Path,
    prompt: str,
    output_path: Path,
) -> list[str]:
    """Codex CLI 実行コマンドを構築する。

    Parameters
    ----------
    codex_command : str
        実行する Codex CLI コマンド。
    workspace : Path
        Codex が作業する workspace。
    prompt : str
        Codex に渡す prompt。
    output_path : Path
        最終メッセージを書き出す一時ファイルのパス。

    Returns
    -------
    list[str]
        `asyncio.create_subprocess_exec` に渡す引数配列。
    """

    return [
        codex_command,
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "-C",
        str(workspace),
        "-o",
        str(output_path),
        prompt,
    ]


def build_codex_prompt(prompt: str) -> str:
    """Codex に渡す実行 prompt を組み立てる。

    Parameters
    ----------
    prompt : str
        ユーザーから受け取った元の prompt。

    Returns
    -------
    str
        配送モード制御の指示を前置した Codex 用 prompt。
    """

    return f"{CODEX_DELIVERY_INSTRUCTION}\n{prompt.strip()}"


def resolve_command_path(command_name: str) -> str:
    """実行可能なコマンドパスを解決する。

    Parameters
    ----------
    command_name : str
        解決対象のコマンド名またはパス。

    Returns
    -------
    str
        実行時に利用する実コマンドパス。

    Raises
    ------
    FileNotFoundError
        コマンドを解決できなかった場合。
    """

    resolved_path = shutil.which(command_name)
    if resolved_path is not None:
        return resolved_path

    for candidate in (f"{command_name}.cmd", f"{command_name}.exe", f"{command_name}.bat"):
        resolved_path = shutil.which(candidate)
        if resolved_path is not None:
            return resolved_path

    raise FileNotFoundError(command_name)


def _create_output_path() -> Path:
    """Codex 最終応答を書き出す一時ファイルを作る。

    Returns
    -------
    Path
        一時ファイルのパス。
    """

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        return Path(temp_file.name)


def _read_output_file(path: Path) -> str:
    """一時ファイルから Codex の最終応答を読む。

    Parameters
    ----------
    path : Path
        読み取り対象の一時ファイルパス。

    Returns
    -------
    str
        ファイル内容。存在しない場合は空文字。
    """

    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _remove_output_file(path: Path) -> None:
    """一時ファイルを削除する。

    Parameters
    ----------
    path : Path
        削除対象の一時ファイルパス。

    Returns
    -------
    None
        存在する場合だけ削除する。
    """

    if path.exists():
        path.unlink()


def _extract_last_message(output_text: str) -> str:
    """Codex の出力から最終メッセージを取り出す。

    Parameters
    ----------
    output_text : str
        `-o` で保存した Codex の最終メッセージ。

    Returns
    -------
    str
        前後空白を除去した最終メッセージ。
    """

    return output_text.strip()
