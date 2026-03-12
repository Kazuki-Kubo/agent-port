"""Prompt を agent と workspace に振り分ける。"""

from __future__ import annotations

from agent_port.agents import AgentRequest, AgentRunResult
from agent_port.registry import AgentStore, RegistryError
from agent_port.workspaces import WorkspaceError, Workspaces


class RouterError(RuntimeError):
    """routing 時のエラーを表す。"""


class Router:
    """既定値を使って agent 実行先を決める。"""

    def __init__(
        self,
        store: AgentStore | None = None,
        workspaces: Workspaces | None = None,
        default_agent: str | None = None,
        default_workspace: str | None = None,
        **legacy: object,
    ) -> None:
        """router を初期化する。

        Parameters
        ----------
        store : AgentStore
            Agent 実行器の registry。
        workspaces : Workspaces
            workspace registry。
        default_agent : str
            既定 backend 名。
        default_workspace : str
            既定 workspace ID。
        **legacy : object
            旧引数名との互換用引数。
        """

        resolved_store = store or legacy.get("registry")
        resolved_workspaces = workspaces or legacy.get("workspace_registry")
        resolved_default_agent = default_agent or legacy.get("default_backend")
        resolved_default_workspace = (
            default_workspace or legacy.get("default_workspace_id")
        )

        if not isinstance(resolved_store, AgentStore):
            raise TypeError("store が必要です。")
        if not isinstance(resolved_workspaces, Workspaces):
            raise TypeError("workspaces が必要です。")
        if not isinstance(resolved_default_agent, str):
            raise TypeError("default_agent が必要です。")
        if not isinstance(resolved_default_workspace, str):
            raise TypeError("default_workspace が必要です。")

        self._store = resolved_store
        self._workspaces = resolved_workspaces
        self._default_agent = resolved_default_agent
        self._default_workspace = resolved_default_workspace

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """request を実行する。

        Parameters
        ----------
        request : AgentRequest
            実行要求。

        Returns
        -------
        AgentRunResult
            実行結果。
        """

        backend = request.backend_name or self._default_agent
        workspace_id = request.workspace_id or self._default_workspace

        try:
            runner = self._store.get(backend)
        except RegistryError as exc:
            raise RouterError(str(exc)) from exc

        try:
            workspace = self._workspaces.get(workspace_id)
        except WorkspaceError as exc:
            raise RouterError(str(exc)) from exc

        if not workspace.supports(backend):
            raise RouterError(
                "workspace がこの agent backend を許可していません: "
                f"workspace_id={workspace_id} backend={backend}"
            )

        return await runner.run(
            AgentRequest(
                prompt=request.prompt,
                backend_name=backend,
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
        """prompt だけ指定して実行する。

        Parameters
        ----------
        prompt : str
            実行する本文。
        backend_name : str | None, default=None
            明示する backend 名。
        workspace_id : str | None, default=None
            明示する workspace ID。

        Returns
        -------
        AgentRunResult
            実行結果。
        """

        return await self.run(
            AgentRequest(
                prompt=prompt,
                backend_name=backend_name,
                workspace_id=workspace_id,
            )
        )

    def default_backend(self) -> str:
        """既定 backend 名を返す。

        Returns
        -------
        str
            既定 backend 名。
        """

        return self._default_agent

    def default_workspace(self) -> str:
        """既定 workspace ID を返す。

        Returns
        -------
        str
            既定 workspace ID。
        """

        return self._default_workspace

    def get_default_backend(self) -> str:
        """旧名の互換メソッド。

        Returns
        -------
        str
            `default_backend()` の結果。
        """

        return self.default_backend()

    def get_default_workspace_id(self) -> str:
        """旧名の互換メソッド。

        Returns
        -------
        str
            `default_workspace()` の結果。
        """

        return self.default_workspace()


AgentRouter = Router
AgentRouterError = RouterError
