"""Agent の共通型を定義する。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentRequest:
    """Agent 実行要求を表す。

    Attributes
    ----------
    prompt : str
        Agent に渡す本文。
    backend_name : str | None, default=None
        実行する backend 名。`None` のときは既定値を使う。
    workspace_id : str | None, default=None
        対象 workspace の ID。`None` のときは既定値を使う。
    workspace_path : Path | None, default=None
        解決済みの workspace パス。
    """

    prompt: str
    backend_name: str | None = None
    workspace_id: str | None = None
    workspace_path: Path | None = None


@dataclass(frozen=True)
class AgentRunResult:
    """Agent 実行結果を表す。

    Attributes
    ----------
    backend_name : str
        実行した backend 名。
    workspace_id : str
        実行した workspace ID。
    message : str
        ユーザーへ返す本文。
    raw_output : str
        Agent 側の生出力。
    """

    backend_name: str
    workspace_id: str
    message: str
    raw_output: str


class AgentRunner(ABC):
    """Agent 実行器の共通インターフェース。"""

    @abstractmethod
    def get_backend_name(self) -> str:
        """backend 名を返す。

        Returns
        -------
        str
            registry に登録する backend 名。
        """

    @abstractmethod
    async def run(self, request: AgentRequest) -> AgentRunResult:
        """Agent を実行する。

        Parameters
        ----------
        request : AgentRequest
            実行要求。

        Returns
        -------
        AgentRunResult
            実行結果。
        """
