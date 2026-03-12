"""Agent 実装を backend 名で管理するレジストリ。"""

from __future__ import annotations

from typing import Iterable

from agent_port.agents import AgentRunner


class AgentRegistryError(RuntimeError):
    """Agent registry の構築や参照に失敗した場合の例外。"""


class AgentRegistry:
    """利用可能な Agent 実装を backend 名で保持する。"""

    def __init__(self, runners: Iterable[AgentRunner] | None = None) -> None:
        """Registry を初期化する。

        Parameters
        ----------
        runners : Iterable[AgentRunner] | None, default=None
            初期登録する Agent 実装一覧。

        Returns
        -------
        None
            空または初期値入りの registry を構築する。
        """

        self._runners: dict[str, AgentRunner] = {}
        for runner in runners or []:
            self.register(runner)

    def register(self, runner: AgentRunner) -> None:
        """Agent 実装を登録する。

        Parameters
        ----------
        runner : AgentRunner
            登録する Agent 実装。

        Returns
        -------
        None
            backend 名をキーに Agent 実装を保存する。

        Raises
        ------
        AgentRegistryError
            同じ backend 名が既に登録済みの場合。
        """

        backend_name = runner.get_backend_name()
        if backend_name in self._runners:
            raise AgentRegistryError(
                f"Agent backend は既に登録されています: {backend_name}"
            )
        self._runners[backend_name] = runner

    def get_runner(self, backend_name: str) -> AgentRunner:
        """backend 名から Agent 実装を取得する。

        Parameters
        ----------
        backend_name : str
            取得対象の backend 名。

        Returns
        -------
        AgentRunner
            指定 backend に対応する Agent 実装。

        Raises
        ------
        AgentRegistryError
            backend 名に対応する Agent 実装が存在しない場合。
        """

        if backend_name not in self._runners:
            raise AgentRegistryError(
                f"Agent backend が登録されていません: {backend_name}"
            )
        return self._runners[backend_name]

    def list_backends(self) -> tuple[str, ...]:
        """登録済み backend 名一覧を返す。

        Returns
        -------
        tuple[str, ...]
            利用可能な backend 名のタプル。
        """

        return tuple(self._runners.keys())
