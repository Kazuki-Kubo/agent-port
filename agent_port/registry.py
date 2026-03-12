"""Agent 実行器の registry を扱う。"""

from __future__ import annotations

from typing import Iterable

from agent_port.agents import AgentRunner


class RegistryError(RuntimeError):
    """Agent registry のエラーを表す。"""


class AgentStore:
    """Agent 実行器を backend 名で保持する。"""

    def __init__(self, runners: Iterable[AgentRunner] | None = None) -> None:
        """registry を初期化する。

        Parameters
        ----------
        runners : Iterable[AgentRunner] | None, default=None
            初期登録する実行器一覧。
        """

        self._items: dict[str, AgentRunner] = {}
        for runner in runners or []:
            self.add(runner)

    def add(self, runner: AgentRunner) -> None:
        """実行器を追加する。

        Parameters
        ----------
        runner : AgentRunner
            追加する実行器。
        """

        name = runner.get_backend_name()
        if name in self._items:
            raise RegistryError(f"Agent backend は既に登録されています: {name}")
        self._items[name] = runner

    def get(self, name: str) -> AgentRunner:
        """実行器を取得する。

        Parameters
        ----------
        name : str
            backend 名。

        Returns
        -------
        AgentRunner
            対応する実行器。
        """

        if name not in self._items:
            raise RegistryError(f"Agent backend が見つかりません: {name}")
        return self._items[name]

    def names(self) -> tuple[str, ...]:
        """登録済み backend 名を返す。

        Returns
        -------
        tuple[str, ...]
            backend 名一覧。
        """

        return tuple(self._items.keys())

    def register(self, runner: AgentRunner) -> None:
        """旧名の互換メソッド。

        Parameters
        ----------
        runner : AgentRunner
            追加する実行器。

        Returns
        -------
        None
            `add()` を呼ぶ。
        """

        self.add(runner)

    def get_runner(self, backend_name: str) -> AgentRunner:
        """旧名の互換メソッド。

        Parameters
        ----------
        backend_name : str
            backend 名。

        Returns
        -------
        AgentRunner
            `get()` の結果。
        """

        return self.get(backend_name)

    def list_backends(self) -> tuple[str, ...]:
        """旧名の互換メソッド。

        Returns
        -------
        tuple[str, ...]
            `names()` の結果。
        """

        return self.names()


AgentRegistry = AgentStore
AgentRegistryError = RegistryError
