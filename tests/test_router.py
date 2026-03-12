"""router と registry を確認する。"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_port.agents import AgentRequest, AgentRunResult, AgentRunner
from agent_port.registry import AgentRegistry, AgentRegistryError
from agent_port.router import AgentRouter, AgentRouterError
from agent_port.workspaces import ManagedWorkspace, WorkspaceRegistry


@dataclass
class DummyRunner(AgentRunner):
    """テスト用の簡易 runner。"""

    backend_name: str

    def get_backend_name(self) -> str:
        """backend 名を返す。

        Returns
        -------
        str
            登録名。
        """

        return self.backend_name

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """受け取った情報をそのまま返す。

        Parameters
        ----------
        request : AgentRequest
            実行要求。

        Returns
        -------
        AgentRunResult
            確認しやすい結果。
        """

        return AgentRunResult(
            backend_name=self.backend_name,
            workspace_id=request.workspace_id or "unknown",
            delivery_mode="reply",
            message=f"{self.backend_name}:{request.workspace_id}:{request.prompt}",
            raw_output=str(request.workspace_path),
        )


def test_router_uses_default_agent_and_workspace() -> None:
    """既定値で routing されることを確認する。

    Returns
    -------
    None
        backend と workspace の既定値が使われることを確認する。
    """

    router = AgentRouter(
        registry=AgentRegistry([DummyRunner("codex")]),
        workspace_registry=WorkspaceRegistry(
            [
                ManagedWorkspace(
                    workspace_id="sample",
                    path=Path("..").resolve(),
                    allowed_agents=("codex",),
                )
            ]
        ),
        default_backend="codex",
        default_workspace_id="sample",
    )

    result = asyncio.run(router.run_prompt("hello"))

    assert result.backend_name == "codex"
    assert result.workspace_id == "sample"
    assert result.delivery_mode == "reply"
    assert result.message == "codex:sample:hello"


def test_router_uses_explicit_agent_and_workspace() -> None:
    """明示指定が既定値より優先されることを確認する。

    Returns
    -------
    None
        指定した backend と workspace が使われることを確認する。
    """

    router = AgentRouter(
        registry=AgentRegistry([DummyRunner("codex"), DummyRunner("claude_code")]),
        workspace_registry=WorkspaceRegistry(
            [
                ManagedWorkspace(
                    workspace_id="sample",
                    path=Path("..").resolve(),
                    allowed_agents=("codex", "claude_code"),
                ),
                ManagedWorkspace(
                    workspace_id="docs",
                    path=Path("..").resolve(),
                    allowed_agents=("claude_code",),
                ),
            ]
        ),
        default_backend="codex",
        default_workspace_id="sample",
    )

    result = asyncio.run(
        router.run_prompt("hello", backend_name="claude_code", workspace_id="docs")
    )

    assert result.backend_name == "claude_code"
    assert result.workspace_id == "docs"
    assert result.delivery_mode == "reply"
    assert result.message == "claude_code:docs:hello"


def test_registry_rejects_duplicate_backend() -> None:
    """重複 backend を拒否することを確認する。

    Returns
    -------
    None
        同じ backend 名を二重登録できないことを確認する。
    """

    registry = AgentRegistry([DummyRunner("codex")])

    with pytest.raises(AgentRegistryError):
        registry.register(DummyRunner("codex"))


def test_router_rejects_unknown_backend() -> None:
    """未登録 backend を拒否することを確認する。

    Returns
    -------
    None
        未知の backend 名では routing できないことを確認する。
    """

    router = AgentRouter(
        registry=AgentRegistry([DummyRunner("codex")]),
        workspace_registry=WorkspaceRegistry(
            [
                ManagedWorkspace(
                    workspace_id="sample",
                    path=Path("..").resolve(),
                    allowed_agents=("codex",),
                )
            ]
        ),
        default_backend="codex",
        default_workspace_id="sample",
    )

    with pytest.raises(AgentRouterError):
        asyncio.run(router.run_prompt("hello", backend_name="unknown"))


def test_router_rejects_disallowed_pair() -> None:
    """許可されていない workspace と backend の組み合わせを拒否する。

    Returns
    -------
    None
        `allowed_agents` にない backend では実行できないことを確認する。
    """

    router = AgentRouter(
        registry=AgentRegistry([DummyRunner("codex")]),
        workspace_registry=WorkspaceRegistry(
            [
                ManagedWorkspace(
                    workspace_id="docs",
                    path=Path("..").resolve(),
                    allowed_agents=("claude_code",),
                )
            ]
        ),
        default_backend="codex",
        default_workspace_id="docs",
    )

    with pytest.raises(AgentRouterError):
        asyncio.run(router.run_prompt("hello"))
