"""Prompt を適切な Agent 実装と workspace へ振り分けるルータ。"""

from __future__ import annotations

from agent_port.agent_registry import AgentRegistry, AgentRegistryError
from agent_port.agents import AgentRequest, AgentRunResult
from agent_port.workspace_registry import WorkspaceRegistry, WorkspaceRegistryError


class AgentRouterError(RuntimeError):
    """Agent の選択や workspace 解決に失敗した場合の例外。"""


class AgentRouter:
    """既定 backend と既定 workspace に基づいて Agent を選択する。"""

    def __init__(
        self,
        registry: AgentRegistry,
        workspace_registry: WorkspaceRegistry,
        default_backend: str,
        default_workspace_id: str,
    ) -> None:
        """Router を初期化する。

        Parameters
        ----------
        registry : AgentRegistry
            利用可能な Agent 実装を保持する registry。
        workspace_registry : WorkspaceRegistry
            利用可能な workspace を保持する registry。
        default_backend : str
            backend 指定がない場合に使う既定 backend 名。
        default_workspace_id : str
            workspace 指定がない場合に使う既定 workspace ID。

        Returns
        -------
        None
            Agent と workspace の routing に必要な情報を保持する。
        """

        self._registry = registry
        self._workspace_registry = workspace_registry
        self._default_backend = default_backend
        self._default_workspace_id = default_workspace_id

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """要求を適切な Agent と workspace へ振り分けて実行する。

        Parameters
        ----------
        request : AgentRequest
            実行対象の prompt、backend、workspace 情報。

        Returns
        -------
        AgentRunResult
            選択された Agent が返した実行結果。
        """

        backend_name = request.backend_name or self._default_backend
        workspace_id = request.workspace_id or self._default_workspace_id

        try:
            runner = self._registry.get_runner(backend_name)
        except AgentRegistryError as exc:
            raise AgentRouterError(str(exc)) from exc

        try:
            workspace = self._workspace_registry.get_workspace(workspace_id)
        except WorkspaceRegistryError as exc:
            raise AgentRouterError(str(exc)) from exc

        if not workspace.supports_agent(backend_name):
            raise AgentRouterError(
                "workspace がこの agent backend を許可していません: "
                f"workspace_id={workspace_id} backend={backend_name}"
            )

        return await runner.run(
            AgentRequest(
                prompt=request.prompt,
                backend_name=backend_name,
                workspace_id=workspace_id,
                workspace_path=workspace.path,
            )
        )

    async def run_prompt(
        self,
        prompt: str,
        backend_name: str | None = None,
        workspace_id: str | None = None,
    ) -> AgentRunResult:
        """Prompt だけを指定して Agent を実行する。

        Parameters
        ----------
        prompt : str
            実行対象の入力テキスト。
        backend_name : str | None, default=None
            利用する backend 名。未指定時は既定 backend。
        workspace_id : str | None, default=None
            利用する workspace ID。未指定時は既定 workspace。

        Returns
        -------
        AgentRunResult
            Agent が返した最終応答。
        """

        return await self.run(
            AgentRequest(
                prompt=prompt,
                backend_name=backend_name,
                workspace_id=workspace_id,
            )
        )

    def get_default_backend(self) -> str:
        """既定 backend 名を返す。

        Returns
        -------
        str
            backend 指定がない場合に利用する backend 名。
        """

        return self._default_backend

    def get_default_workspace_id(self) -> str:
        """既定 workspace ID を返す。

        Returns
        -------
        str
            workspace 指定がない場合に利用する workspace ID。
        """

        return self._default_workspace_id
