"""Agent registry と router の動作を検証するテスト。"""

import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest

from agent_port.agent_registry import AgentRegistry, AgentRegistryError
from agent_port.agent_router import AgentRouter, AgentRouterError
from agent_port.agents import AgentRequest, AgentRunResult, AgentRunner
from agent_port.workspace_registry import ManagedWorkspace, WorkspaceRegistry


@dataclass
class DummyRunner(AgentRunner):
    """テスト用の簡易 Agent 実装。"""

    backend_name: str

    def get_backend_name(self) -> str:
        """backend 名を返す。"""

        return self.backend_name

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """受け取った prompt と workspace をそのまま返す。"""

        return AgentRunResult(
            backend_name=self.backend_name,
            workspace_id=request.workspace_id or "unknown",
            message=f"{self.backend_name}:{request.workspace_id}:{request.prompt}",
            raw_output=str(request.workspace_path),
        )


def test_agent_router_uses_default_backend_and_workspace() -> None:
    """既定 backend と既定 workspace が選ばれることを検証する。

    Returns
    -------
    None
        指定なし実行で default backend と default workspace が使われることを確認する。
    """

    registry = AgentRegistry([DummyRunner("codex")])
    workspace_registry = WorkspaceRegistry(
        [
            ManagedWorkspace(
                workspace_id="sample",
                path=Path("..").resolve(),
                allowed_agents=("codex",),
            )
        ]
    )
    router = AgentRouter(
        registry=registry,
        workspace_registry=workspace_registry,
        default_backend="codex",
        default_workspace_id="sample",
    )

    result = asyncio.run(router.run_prompt("hello"))

    assert result.backend_name == "codex"
    assert result.workspace_id == "sample"
    assert result.message == "codex:sample:hello"


def test_agent_router_uses_explicit_backend_and_workspace() -> None:
    """明示 backend と workspace が優先されることを検証する。

    Returns
    -------
    None
        指定した backend と workspace の組み合わせで実行されることを確認する。
    """

    registry = AgentRegistry([DummyRunner("codex"), DummyRunner("claude_code")])
    workspace_registry = WorkspaceRegistry(
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
    )
    router = AgentRouter(
        registry=registry,
        workspace_registry=workspace_registry,
        default_backend="codex",
        default_workspace_id="sample",
    )

    result = asyncio.run(
        router.run_prompt(
            "hello",
            backend_name="claude_code",
            workspace_id="docs",
        )
    )

    assert result.backend_name == "claude_code"
    assert result.workspace_id == "docs"
    assert result.message == "claude_code:docs:hello"


def test_agent_registry_rejects_duplicate_backend() -> None:
    """同名 backend の重複登録を拒否することを検証する。"""

    registry = AgentRegistry([DummyRunner("codex")])

    with pytest.raises(AgentRegistryError):
        registry.register(DummyRunner("codex"))


def test_agent_router_rejects_unknown_backend() -> None:
    """未登録 backend 指定を拒否することを検証する。"""

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


def test_agent_router_rejects_disallowed_workspace_agent_pair() -> None:
    """workspace が許可しない backend の実行を拒否することを検証する。"""

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
