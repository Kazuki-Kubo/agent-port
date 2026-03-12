"""複数 Agent を共通で扱うための基底型を定義するモジュール。"""

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
        Agent に渡す入力テキスト。
    backend_name : str | None
        利用する Agent backend 名。`None` の場合は既定 backend を利用する。
    workspace_id : str | None
        実行対象の workspace ID。`None` の場合は既定 workspace を利用する。
    workspace_path : Path | None
        解決済みの workspace path。router が埋める。
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
        実際に応答を返した Agent backend 名。
    workspace_id : str
        実行に使った workspace ID。
    message : str
        チャットツールへ返す最終メッセージ。
    raw_output : str
        Agent CLI や SDK から得た生出力。
    """

    backend_name: str
    workspace_id: str
    message: str
    raw_output: str


class AgentRunner(ABC):
    """個別 Agent 実装が従う共通インターフェース。"""

    @abstractmethod
    def get_backend_name(self) -> str:
        """backend 名を返す。

        Returns
        -------
        str
            Registry から識別するための backend 名。
        """

    @abstractmethod
    async def run(self, request: AgentRequest) -> AgentRunResult:
        """Agent を実行する。

        Parameters
        ----------
        request : AgentRequest
            実行対象の prompt、backend、workspace 情報を持つ要求。

        Returns
        -------
        AgentRunResult
            Agent から得た最終応答。
        """
