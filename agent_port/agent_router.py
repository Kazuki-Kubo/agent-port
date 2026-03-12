"""Prompt を適切な Agent 実装へ振り分けるルータ。"""

from __future__ import annotations

from agent_port.agent_registry import AgentRegistry, AgentRegistryError
from agent_port.agents import AgentRequest, AgentRunResult


class AgentRouterError(RuntimeError):
    """Agent の選択や実行準備に失敗した場合の例外。"""


class AgentRouter:
    """既定 backend または明示 backend に基づいて Agent を選択する。"""

    def __init__(self, registry: AgentRegistry, default_backend: str) -> None:
        """Router を初期化する。

        Parameters
        ----------
        registry : AgentRegistry
            利用可能な Agent 実装を保持する registry。
        default_backend : str
            backend 指定がない場合に使う既定 backend 名。

        Returns
        -------
        None
            Agent ルーティングに必要な情報を保持する。
        """

        self._registry = registry
        self._default_backend = default_backend

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """要求を適切な Agent へ振り分けて実行する。

        Parameters
        ----------
        request : AgentRequest
            実行対象の prompt と任意の backend 指定。

        Returns
        -------
        AgentRunResult
            選択された Agent が返した実行結果。

        Raises
        ------
        AgentRouterError
            指定 backend が未登録の場合。
        """

        backend_name = request.backend_name or self._default_backend
        try:
            runner = self._registry.get_runner(backend_name)
        except AgentRegistryError as exc:
            raise AgentRouterError(str(exc)) from exc
        return await runner.run(
            AgentRequest(prompt=request.prompt, backend_name=backend_name)
        )

    async def run_prompt(
        self,
        prompt: str,
        backend_name: str | None = None,
    ) -> AgentRunResult:
        """Prompt だけを指定して Agent を実行する。

        Parameters
        ----------
        prompt : str
            実行対象の入力テキスト。
        backend_name : str | None, default=None
            利用する backend 名。未指定時は既定 backend を使う。

        Returns
        -------
        AgentRunResult
            Agent が返した最終応答。
        """

        return await self.run(AgentRequest(prompt=prompt, backend_name=backend_name))

    def get_default_backend(self) -> str:
        """既定 backend 名を返す。

        Returns
        -------
        str
            backend 指定がない場合に利用する backend 名。
        """

        return self._default_backend
