"""Discord と Agent を中継するブリッジ。"""

from __future__ import annotations

import logging

import discord

from agent_port.agent_router import AgentRouter, AgentRouterError
from agent_port.codex_runner import CodexExecutionError
from agent_port.config import AppConfig
from agent_port.discord_io import (
    DiscordPrompt,
    build_discord_thread_name,
    extract_discord_delivery,
    extract_discord_prompt,
    send_discord_response,
    send_discord_text,
    split_discord_message,
)


class DiscordAgentBridgeClient(discord.Client):
    """Discord メッセージを Agent へ中継する Client。"""

    def __init__(self, config: AppConfig, agent_router: AgentRouter) -> None:
        """Discord bridge を初期化する。

        Parameters
        ----------
        config : AppConfig
            Discord 側の設定。
        agent_router : AgentRouter
            Prompt を適切な Agent へ振り分ける router。

        Returns
        -------
        None
            Discord Client と依存オブジェクトを構築する。
        """

        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._config = config
        self._agent_router = agent_router
        self._logger = logging.getLogger(__name__)

    async def on_ready(self) -> None:
        """Bot 接続完了時に設定をログ出力する。

        Returns
        -------
        None
            接続済み Bot 名と trigger mode をログへ出力する。
        """

        if self.user is None:
            return

        self._logger.info(
            "Discord Bot connected as %s with trigger_mode %s default_agent=%s default_workspace=%s",
            self.user,
            self._config.discord_trigger_mode,
            self._agent_router.get_default_backend(),
            self._agent_router.get_default_workspace_id(),
        )

    async def on_message(self, message: discord.Message) -> None:
        """Discord メッセージを受信して Agent を実行する。

        Parameters
        ----------
        message : discord.Message
            受信した Discord メッセージ。

        Returns
        -------
        None
            条件に合うメッセージだけ中継し、同じチャンネルへ返信する。
        """

        if message.author.bot:
            self._logger.debug(
                "Ignoring bot message channel=%s author=%s",
                getattr(message.channel, "id", "unknown"),
                message.author,
            )
            return

        is_bot_mentioned = self._is_trigger_mentioned(message)
        self._logger.info(
            "Received Discord message channel=%s author=%s trigger_mode=%s mentioned=%s content_length=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            self._config.discord_trigger_mode,
            is_bot_mentioned,
            len(message.content),
        )
        prompt = extract_discord_prompt(
            content=message.content,
            trigger_mode=self._config.discord_trigger_mode,
            bot_user_id=self.user.id if self.user is not None else None,
            is_bot_mentioned=is_bot_mentioned,
        )
        if prompt is None:
            self._logger.info(
                "Ignoring message channel=%s author=%s because trigger did not match or prompt was empty",
                getattr(message.channel, "id", "unknown"),
                message.author,
            )
            if self._config.discord_trigger_mode == "mention" and is_bot_mentioned:
                await send_discord_text(
                    message,
                    "Bot をメンションしたあとに本文も送ってください。",
                )
            return

        self._logger.info(
            "Executing agent for channel=%s author=%s prompt_length=%s backend=%s workspace_id=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            len(prompt.prompt),
            self._agent_router.get_default_backend(),
            self._agent_router.get_default_workspace_id(),
        )
        async with message.channel.typing():
            try:
                result = await self._agent_router.run_prompt(prompt.prompt)
            except (AgentRouterError, CodexExecutionError) as exc:
                self._logger.exception(
                    "Agent execution failed channel=%s author=%s",
                    getattr(message.channel, "id", "unknown"),
                    message.author,
                )
                await send_discord_text(message, f"Agent 実行エラー:\n{exc}")
                return

        self._logger.info(
            "Sending Discord response channel=%s author=%s backend=%s workspace_id=%s response_length=%s delivery_mode=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            result.backend_name,
            result.workspace_id,
            len(result.message),
            extract_discord_delivery(result.message).mode,
        )
        delivery = extract_discord_delivery(result.message)
        await send_discord_response(message, delivery.message, delivery.mode)

    def _is_trigger_mentioned(self, message: discord.Message) -> bool:
        """Bot または Bot ロールがメンションされたか判定する。

        Parameters
        ----------
        message : discord.Message
            判定対象の Discord メッセージ。

        Returns
        -------
        bool
            Bot 本体または Bot ロールがメンションされていれば `True`。
        """

        if self.user is not None and self.user.mentioned_in(message):
            return True

        if message.guild is None or self.user is None:
            return False

        bot_member = message.guild.get_member(self.user.id)
        if bot_member is None:
            return False

        bot_role_ids = {role.id for role in bot_member.roles}
        mentioned_role_ids = {role.id for role in message.role_mentions}
        return bool(bot_role_ids & mentioned_role_ids)
DiscordCodexBridgeClient = DiscordAgentBridgeClient
