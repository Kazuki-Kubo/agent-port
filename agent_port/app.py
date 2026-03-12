"""アプリケーション起動処理をまとめるモジュール。"""

from __future__ import annotations

import asyncio
import logging

from agent_port.registry import AgentRegistry
from agent_port.router import AgentRouter
from agent_port.codex import CodexRunner
from agent_port.config import AppConfig, ConfigError
from agent_port.discord_bot import DiscordBot


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
        f"default_workspace_id={config.default_workspace_id}",
        f"available_agent_backends={','.join(config.list_agent_backends())}",
        f"available_workspace_ids={','.join(config.list_workspace_ids())}",
        f"workspace_registry_path={config.workspace_registry_path or '(legacy env)'}",
        f"default_workspace_path={config.agent_workspace}",
        f"discord_trigger_mode={config.discord_trigger_mode}",
        f"codex_command={config.codex_command}",
        f"log_level={config.log_level}",
    ]
    return "\n".join(lines)


def main() -> None:
    """環境変数から設定を読み込み、起動処理を実行する。"""

    config = AppConfig.from_env()
    configure_logging(config.log_level)
    logging.getLogger(__name__).info(build_startup_summary(config))
    run_application(config)


def configure_logging(log_level: str) -> None:
    """ロギングを初期化する。"""

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_agent_registry(config: AppConfig) -> AgentRegistry:
    """設定から Agent registry を構築する。"""

    return AgentRegistry([CodexRunner(config.codex_config)])


def build_agent_router(config: AppConfig) -> AgentRouter:
    """設定から Agent router を構築する。"""

    registry = build_agent_registry(config)
    return AgentRouter(
        registry=registry,
        workspace_registry=config.workspace_registry,
        default_backend=config.default_agent_backend,
        default_workspace_id=config.default_workspace_id,
    )


def run_application(config: AppConfig) -> None:
    """設定に基づいてアプリケーションを起動する。"""

    if config.chat_backend != "discord":
        raise ConfigError(
            "現在の最小実装で対応している chat backend は discord のみです。"
        )

    asyncio.run(run_discord_agent_bridge(config))


async def run_discord_agent_bridge(config: AppConfig) -> None:
    """Discord から Agent へ中継する bridge を起動する。"""

    agent_router = build_agent_router(config)
    client = DiscordBot(config=config, agent_router=agent_router)
    await client.start(config.discord_bot_token)
