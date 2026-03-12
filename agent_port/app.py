"""アプリケーション起動処理をまとめるモジュール。"""

from __future__ import annotations

import asyncio
import logging

from agent_port.agent_registry import AgentRegistry
from agent_port.agent_router import AgentRouter
from agent_port.codex_runner import CodexRunner
from agent_port.config import AppConfig, ConfigError
from agent_port.discord_bridge import DiscordAgentBridgeClient


def build_startup_summary(config: AppConfig) -> str:
    """起動時に表示する設定要約を組み立てる。

    Parameters
    ----------
    config : AppConfig
        表示対象のアプリケーション設定。

    Returns
    -------
    str
        起動ログに出す複数行の設定要約。
    """

    lines = [
        "agent-port is ready.",
        f"chat_backend={config.chat_backend}",
        f"default_agent_backend={config.default_agent_backend}",
        f"available_agent_backends={','.join(config.list_agent_backends())}",
        f"discord_trigger_mode={config.discord_trigger_mode}",
        f"agent_workspace={config.agent_workspace}",
        f"codex_command={config.codex_command}",
        f"log_level={config.log_level}",
    ]
    return "\n".join(lines)


def main() -> None:
    """環境変数から設定を読み込み、起動処理を実行する。

    Returns
    -------
    None
        ログ設定後にアプリケーションを起動する。
    """

    config = AppConfig.from_env()
    configure_logging(config.log_level)
    logging.getLogger(__name__).info(build_startup_summary(config))
    run_application(config)


def configure_logging(log_level: str) -> None:
    """ロギングを初期化する。

    Parameters
    ----------
    log_level : str
        ログ出力レベル。

    Returns
    -------
    None
        標準出力向けの logging 設定を適用する。
    """

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_agent_registry(config: AppConfig) -> AgentRegistry:
    """設定から Agent registry を構築する。

    Parameters
    ----------
    config : AppConfig
        Agent backend 設定を含むアプリケーション設定。

    Returns
    -------
    AgentRegistry
        利用可能な Agent 実装を登録済みの registry。
    """

    return AgentRegistry([CodexRunner(config.codex_config)])


def build_agent_router(config: AppConfig) -> AgentRouter:
    """設定から Agent router を構築する。

    Parameters
    ----------
    config : AppConfig
        既定 backend を含むアプリケーション設定。

    Returns
    -------
    AgentRouter
        registry と既定 backend を保持する router。
    """

    registry = build_agent_registry(config)
    return AgentRouter(
        registry=registry,
        default_backend=config.default_agent_backend,
    )


def run_application(config: AppConfig) -> None:
    """設定に基づいてアプリケーションを起動する。

    Parameters
    ----------
    config : AppConfig
        起動対象の設定。

    Returns
    -------
    None
        対応 backend を起動する。

    Raises
    ------
    ConfigError
        未対応の chat backend が指定された場合。
    """

    if config.chat_backend != "discord":
        raise ConfigError(
            "現在の最小実装で対応している chat backend は discord のみです。"
        )

    asyncio.run(run_discord_agent_bridge(config))


async def run_discord_agent_bridge(config: AppConfig) -> None:
    """Discord から Agent へ中継する bridge を起動する。

    Parameters
    ----------
    config : AppConfig
        Discord と Agent 設定を含むアプリケーション設定。

    Returns
    -------
    None
        Bot 終了まで待機する。
    """

    agent_router = build_agent_router(config)
    client = DiscordAgentBridgeClient(config=config, agent_router=agent_router)
    await client.start(config.discord_bot_token)
