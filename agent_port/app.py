"""アプリ起動処理をまとめる。"""

from __future__ import annotations

import asyncio
import logging

from agent_port.codex import CodexRunner
from agent_port.config import AppConfig, ConfigError
from agent_port.discord_bot import DiscordBot
from agent_port.registry import AgentStore
from agent_port.router import Router


def build_startup_summary(config: AppConfig) -> str:
    """起動時の設定サマリーを作る。

    Parameters
    ----------
    config : AppConfig
        表示対象の設定。

    Returns
    -------
    str
        複数行の要約文字列。
    """

    lines = [
        "agent-port is ready.",
        f"chat={config.chat}",
        f"default_agent={config.default_agent}",
        f"default_workspace={config.default_workspace}",
        f"agents={','.join(config.list_backends())}",
        f"workspaces={','.join(config.list_workspace_ids())}",
        f"workspace_file={config.workspace_file or '(legacy env)'}",
        f"workspace_dir={config.workspace}",
        f"discord_trigger={config.discord_trigger}",
        f"codex_command={config.codex_command}",
        f"log_level={config.log_level}",
    ]
    return "\n".join(lines)


def main() -> None:
    """環境変数から設定を読み、アプリを起動する。

    Returns
    -------
    None
        起動に必要な処理を順に実行する。
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
        設定するログレベル。

    Returns
    -------
    None
        `logging.basicConfig` を設定する。
    """

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def build_store(config: AppConfig) -> AgentStore:
    """Agent registry を作る。

    Parameters
    ----------
    config : AppConfig
        利用する設定。

    Returns
    -------
    AgentStore
        初期化済み registry。
    """

    return AgentStore([CodexRunner(config.codex)])


def build_router(config: AppConfig) -> Router:
    """router を作る。

    Parameters
    ----------
    config : AppConfig
        利用する設定。

    Returns
    -------
    Router
        初期化済み router。
    """

    return Router(
        store=build_store(config),
        workspaces=config.workspaces,
        default_agent=config.default_agent,
        default_workspace=config.default_workspace,
    )


def run_application(config: AppConfig) -> None:
    """chat backend を起動する。

    Parameters
    ----------
    config : AppConfig
        利用する設定。

    Returns
    -------
    None
        対応する chat backend を起動する。
    """

    if config.chat != "discord":
        raise ConfigError("現在の最小実装で使える chat backend は discord のみです。")

    asyncio.run(run_discord(config))


async def run_discord(config: AppConfig) -> None:
    """Discord Bot を起動する。

    Parameters
    ----------
    config : AppConfig
        利用する設定。

    Returns
    -------
    None
        Discord Bot を接続する。
    """

    bot = DiscordBot(config=config, agent_router=build_router(config))
    await bot.start(config.discord_token)


build_agent_registry = build_store
build_agent_router = build_router
run_discord_agent_bridge = run_discord
