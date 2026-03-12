"""Codex CLI を呼び出す Agent 実装。"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import shutil
import tempfile

from agent_port.agents import AgentRequest, AgentRunResult, AgentRunner
from agent_port.config import CodexConfig

DELIVERY_PROMPT = """Discord へ返す形式を守ってください。
1. 1 行目には `[delivery:reply]` または `[delivery:thread]` を必ず書いてください。
2. 2 行目以降に、Discord へ返す日本語の本文だけを書いてください。
3. 余計な前置きや説明は入れないでください。
4. 通常は `reply` を選び、長文や継続議論だけ `thread` を選んでください。
"""


class CodexError(RuntimeError):
    """Codex 実行時のエラーを表す。"""


class CodexRunner(AgentRunner):
    """Codex CLI で prompt を実行する。"""

    def __init__(self, config: CodexConfig) -> None:
        """runner を初期化する。

        Parameters
        ----------
        config : CodexConfig
            Codex 設定。
        """

        self._config = config
        self._log = logging.getLogger(__name__)

    def get_backend_name(self) -> str:
        """backend 名を返す。

        Returns
        -------
        str
            backend 名。
        """

        return self._config.name

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """request を Codex で実行する。

        Parameters
        ----------
        request : AgentRequest
            実行要求。

        Returns
        -------
        AgentRunResult
            実行結果。
        """

        if request.workspace_id is None or request.workspace_path is None:
            raise CodexError("Codex 実行には workspace が必要です。")

        return await self.run_prompt(
            prompt=request.prompt,
            workspace_id=request.workspace_id,
            workspace_dir=request.workspace_path,
        )

    async def run_prompt(
        self,
        prompt: str,
        workspace_id: str,
        workspace_dir: Path,
    ) -> AgentRunResult:
        """workspace を指定して Codex を実行する。

        Parameters
        ----------
        prompt : str
            実行する本文。
        workspace_id : str
            対象 workspace ID。
        workspace_dir : Path
            対象 workspace の実パス。

        Returns
        -------
        AgentRunResult
            実行結果。
        """

        text = prompt.strip()
        if not text:
            raise CodexError("Codex に渡す prompt は空にできません。")

        out_file = _make_out_file()
        cmd = build_codex_exec_command(
            codex_command=resolve_command_path(self._config.command),
            workspace=workspace_dir,
            prompt=build_codex_prompt(text),
            output_path=out_file,
        )
        proc: asyncio.subprocess.Process | None = None
        stdout = b""
        self._log.info(
            "Starting Codex command workspace_id=%s workspace=%s timeout=%s prompt_length=%s",
            workspace_id,
            workspace_dir,
            self._config.timeout,
            len(text),
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(
                proc.communicate(),
                timeout=self._config.timeout,
            )
        except FileNotFoundError as exc:
            raise CodexError(
                f"Codex CLI コマンドが見つかりません: {self._config.command}"
            ) from exc
        except TimeoutError as exc:
            if proc is not None:
                proc.kill()
                await proc.communicate()
            raise CodexError("Codex CLI の実行がタイムアウトしました。") from exc
        finally:
            out_text = _read_out_file(out_file)
            _remove_out_file(out_file)

        raw = stdout.decode("utf-8", errors="replace")
        if proc is None:
            raise CodexError("Codex CLI プロセスを起動できませんでした。")
        if proc.returncode != 0:
            raise CodexError(
                "Codex CLI の実行に失敗しました。\n"
                f"returncode={proc.returncode}\n"
                f"{raw.strip()}"
            )

        message = _last_message(out_text) or _last_message(raw)
        if not message:
            raise CodexError("Codex CLI から応答を取得できませんでした。")

        self._log.info(
            "Codex command completed workspace_id=%s returncode=%s response_length=%s",
            workspace_id,
            proc.returncode,
            len(message),
        )
        return AgentRunResult(
            backend_name=self.get_backend_name(),
            workspace_id=workspace_id,
            message=message,
            raw_output=raw,
        )


def build_codex_exec_command(
    codex_command: str,
    workspace: Path,
    prompt: str,
    output_path: Path,
) -> list[str]:
    """Codex 実行コマンドを組み立てる。

    Parameters
    ----------
    codex_command : str
        実行するコマンド。
    workspace : Path
        workspace の実パス。
    prompt : str
        Codex に渡す prompt。
    output_path : Path
        出力保存先。

    Returns
    -------
    list[str]
        `create_subprocess_exec` に渡す引数一覧。
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
    """Codex に渡す prompt を組み立てる。

    Parameters
    ----------
    prompt : str
        ユーザー本文。

    Returns
    -------
    str
        配送ルールを前置きした prompt。
    """

    return f"{DELIVERY_PROMPT}\n{prompt.strip()}"


def resolve_command_path(command_name: str) -> str:
    """実行可能な Codex コマンドパスを解決する。

    Parameters
    ----------
    command_name : str
        設定上のコマンド名。

    Returns
    -------
    str
        実行に使うコマンド。
    """

    resolved = shutil.which(command_name)
    if resolved is not None:
        return resolved

    for suffix in (".cmd", ".exe", ".bat"):
        resolved = shutil.which(f"{command_name}{suffix}")
        if resolved is not None:
            return resolved

    raise FileNotFoundError(command_name)


def _make_out_file() -> Path:
    """一時出力ファイルを作る。

    Returns
    -------
    Path
        一時ファイルのパス。
    """

    with tempfile.NamedTemporaryFile(delete=False) as temp:
        return Path(temp.name)


def _read_out_file(path: Path) -> str:
    """一時出力ファイルを読む。

    Parameters
    ----------
    path : Path
        読み込むパス。

    Returns
    -------
    str
        ファイル内容。なければ空文字。
    """

    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _remove_out_file(path: Path) -> None:
    """一時出力ファイルを削除する。

    Parameters
    ----------
    path : Path
        削除するパス。

    Returns
    -------
    None
        存在すれば削除する。
    """

    if path.exists():
        path.unlink()


def _last_message(output_text: str) -> str:
    """最終メッセージ文字列を返す。

    Parameters
    ----------
    output_text : str
        生の出力文字列。

    Returns
    -------
    str
        整形後の文字列。
    """

    return output_text.strip()


CodexExecutionError = CodexError
CodexRunResult = AgentRunResult
