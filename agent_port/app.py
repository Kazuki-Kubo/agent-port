"""アプリケーションの起動処理を提供するモジュール。"""

from __future__ import annotations

import asyncio
import logging

from agent_port.codex_runner import CodexRunner
from agent_port.config import AppConfig, ConfigError
from agent_port.discord_bridge import DiscordCodexBridgeClient


def build_startup_summary(config: AppConfig) -> str:
    """起動時に表示する設定サマリーを生成する。

    Parameters
    ----------
    config : AppConfig
        表示対象のアプリケーション設定。

    Returns
    -------
    str
        利用中のバックエンドや Discord トリガー方式を含む表示文字列。
    """

    lines = [
        "agent-port is ready.",
        f"chat_backend={config.chat_backend}",
        f"agent_backend={config.agent_backend}",
        f"discord_trigger_mode={config.discord_trigger_mode}",
        f"agent_workspace={config.agent_workspace}",
        f"codex_command={config.codex_command}",
        f"log_level={config.log_level}",
    ]
    return "\n".join(lines)


def main() -> None:
    """環境変数から設定を読み込み、対応する実行経路を起動する。

    Returns
    -------
    None
        サポート済みのバックエンドなら Bot を起動し、そうでなければ例外を送出する。
    """

    config = AppConfig.from_env()
    configure_logging(config.log_level)
    logging.getLogger(__name__).info(build_startup_summary(config))
    run_application(config)


def configure_logging(log_level: str) -> None:
    """アプリケーション全体のログ設定を行う。

    Parameters
    ----------
    log_level : str
        設定するログレベル名。

    Returns
    -------
    None
        標準出力向けの基本ログ設定を有効化する。
    """

    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def run_application(config: AppConfig) -> None:
    """対応するバックエンド構成でアプリケーションを起動する。

    Parameters
    ----------
    config : AppConfig
        実行対象の設定。

    Returns
    -------
    None
        Discord と Codex の最小ブリッジを起動する。

    Raises
    ------
    ConfigError
        未対応のバックエンド構成が指定された場合。
    """

    if config.chat_backend != "discord" or config.agent_backend != "codex":
        raise ConfigError(
            "現在の最小実装で対応している組み合わせは "
            "AGENT_PORT_CHAT_BACKEND=discord と "
            "AGENT_PORT_AGENT_BACKEND=codex のみです。"
        )

    asyncio.run(run_discord_codex_bridge(config))


async def run_discord_codex_bridge(config: AppConfig) -> None:
    """Discord と Codex を接続する最小ブリッジを起動する。

    Parameters
    ----------
    config : AppConfig
        Discord と Codex 実行に必要な設定。

    Returns
    -------
    None
        Bot の接続が終了するまで待機する。
    """

    codex_runner = CodexRunner(config)
    client = DiscordCodexBridgeClient(config=config, codex_runner=codex_runner)
    await client.start(config.discord_bot_token)
