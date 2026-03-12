"""Agent registry と router の動作を検証するテスト。"""

import asyncio
from dataclasses import dataclass

import pytest

from agent_port.agent_registry import AgentRegistry, AgentRegistryError
from agent_port.agent_router import AgentRouter, AgentRouterError
from agent_port.agents import AgentRequest, AgentRunResult, AgentRunner


@dataclass
class DummyRunner(AgentRunner):
    """テスト用の簡易 Agent 実装。"""

    backend_name: str

    def get_backend_name(self) -> str:
        """backend 名を返す。

        Returns
        -------
        str
            このダミー実装の backend 名。
        """

        return self.backend_name

    async def run(self, request: AgentRequest) -> AgentRunResult:
        """受け取った prompt をそのまま返す。

        Parameters
        ----------
        request : AgentRequest
            実行対象の prompt。

        Returns
        -------
        AgentRunResult
            backend 名と prompt をそのまま含む結果。
        """

        return AgentRunResult(
            backend_name=self.backend_name,
            message=f"{self.backend_name}:{request.prompt}",
            raw_output=request.prompt,
        )


def test_agent_router_uses_default_backend() -> None:
    """backend 指定なしでは既定 backend が選ばれることを検証する。

    Returns
    -------
    None
        既定 backend の runner が実行されることを確認する。
    """

    registry = AgentRegistry([DummyRunner("codex")])
    router = AgentRouter(registry=registry, default_backend="codex")

    result = asyncio.run(router.run_prompt("hello"))

    assert result.backend_name == "codex"
    assert result.message == "codex:hello"


def test_agent_router_uses_explicit_backend() -> None:
    """明示 backend 指定が優先されることを検証する。

    Returns
    -------
    None
        指定した backend の runner が実行されることを確認する。
    """

    registry = AgentRegistry([DummyRunner("codex"), DummyRunner("claude_code")])
    router = AgentRouter(registry=registry, default_backend="codex")

    result = asyncio.run(router.run_prompt("hello", backend_name="claude_code"))

    assert result.backend_name == "claude_code"
    assert result.message == "claude_code:hello"


def test_agent_registry_rejects_duplicate_backend() -> None:
    """同名 backend の重複登録を拒否することを検証する。

    Returns
    -------
    None
        重複登録時に `AgentRegistryError` になることを確認する。
    """

    registry = AgentRegistry([DummyRunner("codex")])

    with pytest.raises(AgentRegistryError):
        registry.register(DummyRunner("codex"))


def test_agent_router_rejects_unknown_backend() -> None:
    """未登録 backend 指定を拒否することを検証する。

    Returns
    -------
    None
        `AgentRouterError` が送出されることを確認する。
    """

    router = AgentRouter(
        registry=AgentRegistry([DummyRunner("codex")]),
        default_backend="codex",
    )

    with pytest.raises(AgentRouterError):
        asyncio.run(router.run_prompt("hello", backend_name="unknown"))
