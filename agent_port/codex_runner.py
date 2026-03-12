"""Codex CLI を呼び出す最小のランナー。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import asyncio
import shutil
import tempfile

from agent_port.config import AppConfig


class CodexExecutionError(RuntimeError):
    """Codex CLI の実行に失敗した場合に送出する例外。"""


@dataclass(frozen=True)
class CodexRunResult:
    """Codex 実行結果を保持する。

    Attributes
    ----------
    message : str
        Discord へ返す最終メッセージ。
    raw_output : str
        Codex CLI の標準出力と標準エラーの結合結果。
    """

    message: str
    raw_output: str


class CodexRunner:
    """Codex CLI を実行して最終応答を取り出す。"""

    def __init__(self, config: AppConfig) -> None:
        """設定を保持してランナーを初期化する。

        Parameters
        ----------
        config : AppConfig
            Codex 実行時に使うアプリケーション設定。

        Returns
        -------
        None
            設定を保持したランナーを生成する。
        """

        self._config = config

    async def run_prompt(self, prompt: str) -> CodexRunResult:
        """workspace を指定して Codex CLI を実行する。

        Parameters
        ----------
        prompt : str
            Codex へ渡すユーザープロンプト。

        Returns
        -------
        CodexRunResult
            Discord へ返せる最終応答と生の CLI 出力。

        Raises
        ------
        CodexExecutionError
            Codex 実行が失敗した場合や、応答を取得できなかった場合。
        """

        normalized_prompt = prompt.strip()
        if not normalized_prompt:
            raise CodexExecutionError("Codex へ渡すプロンプトが空です。")

        output_path = _create_output_path()
        command = build_codex_exec_command(
            codex_command=resolve_command_path(self._config.codex_command),
            workspace=self._config.agent_workspace,
            prompt=normalized_prompt,
            output_path=output_path,
        )
        process: asyncio.subprocess.Process | None = None
        stdout_bytes = b""

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout_bytes, _ = await asyncio.wait_for(
                process.communicate(),
                timeout=self._config.codex_timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise CodexExecutionError(
                f"Codex CLI コマンドが見つかりません: {self._config.codex_command}"
            ) from exc
        except TimeoutError as exc:
            if process is not None:
                process.kill()
                await process.communicate()
            raise CodexExecutionError(
                "Codex CLI の実行がタイムアウトしました。"
            ) from exc
        finally:
            raw_message = _read_output_file(output_path)
            _remove_output_file(output_path)

        raw_output = stdout_bytes.decode("utf-8", errors="replace")
        if process is None:
            raise CodexExecutionError("Codex CLI プロセスを開始できませんでした。")

        if process.returncode != 0:
            raise CodexExecutionError(
                "Codex CLI の実行に失敗しました。\n"
                f"returncode={process.returncode}\n"
                f"{raw_output.strip()}"
            )

        final_message = _extract_last_message(raw_message)
        if not final_message:
            raise CodexExecutionError(
                "Codex CLI から最終メッセージを取得できませんでした。"
            )

        return CodexRunResult(message=final_message, raw_output=raw_output)


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
        実行する Codex CLI コマンド名。
    workspace : Path
        Codex に渡す workspace。
    prompt : str
        Codex へ渡すプロンプト。
    output_path : Path
        最終メッセージを書き出す一時ファイルのパス。

    Returns
    -------
    list[str]
        `asyncio.create_subprocess_exec` に渡す引数列。
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


def resolve_command_path(command_name: str) -> str:
    """実行可能なコマンドパスを解決する。

    Parameters
    ----------
    command_name : str
        解決対象のコマンド名またはパス。

    Returns
    -------
    str
        `subprocess` へ渡せる実行可能ファイルのパス。

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
    """Codex の最終応答を書き出す一時ファイルを作る。

    Returns
    -------
    Path
        作成した一時ファイルのパス。
    """

    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        return Path(temp_file.name)


def _read_output_file(path: Path) -> str:
    """一時ファイルから Codex の最終応答を読む。

    Parameters
    ----------
    path : Path
        読み込む一時ファイルのパス。

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
        ファイルが存在する場合のみ削除する。
    """

    if path.exists():
        path.unlink()


def _extract_last_message(output_text: str) -> str:
    """Codex の出力ファイルから最終メッセージ部分を取り出す。

    Parameters
    ----------
    output_text : str
        `--output-last-message` で得たファイル内容。

    Returns
    -------
    str
        最終メッセージ本文。取得できなければ空文字。
    """

    stripped_text = output_text.strip()
    if not stripped_text:
        return ""
    return stripped_text
