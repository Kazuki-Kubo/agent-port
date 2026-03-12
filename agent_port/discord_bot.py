"""Discord と Agent を中継する client を定義する。"""

from __future__ import annotations

import logging

import discord

from agent_port.codex import CodexError
from agent_port.config import AppConfig
from agent_port.discord_io import (
    choose_discord_delivery_mode,
    extract_discord_prompt,
    send_discord_response,
    send_discord_text,
)
from agent_port.router import Router, RouterError


class DiscordBot(discord.Client):
    """Discord と Agent の中継を行う Discord client。"""

    def __init__(self, config: AppConfig, agent_router: Router) -> None:
        """client を初期化する。

        Parameters
        ----------
        config : AppConfig
            Discord 側の設定。
        agent_router : Router
            prompt を agent に流す router。
        """

        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._config = config
        self._router = agent_router
        self._logger = logging.getLogger(__name__)

    async def on_ready(self) -> None:
        """接続完了ログを出す。

        Returns
        -------
        None
            Bot 名と既定設定をログに出す。
        """

        if self.user is None:
            return

        self._logger.info(
            "Discord Bot connected as %s with trigger_mode %s default_agent=%s default_workspace=%s",
            self.user,
            self._config.discord_trigger,
            self._router.default_backend(),
            self._router.default_workspace(),
        )

    async def on_message(self, message: discord.Message) -> None:
        """受信メッセージを Agent に中継する。

        Parameters
        ----------
        message : discord.Message
            受信した Discord メッセージ。

        Returns
        -------
        None
            条件に合うメッセージだけ中継する。
        """

        if message.author.bot:
            self._logger.debug(
                "Ignoring bot message channel=%s author=%s",
                getattr(message.channel, "id", "unknown"),
                message.author,
            )
            return

        mentioned = self._is_trigger_mentioned(message)
        self._logger.info(
            "Received Discord message channel=%s author=%s trigger_mode=%s mentioned=%s content_length=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            self._config.discord_trigger,
            mentioned,
            len(message.content),
        )
        prompt = extract_discord_prompt(
            content=message.content,
            trigger_mode=self._config.discord_trigger,
            bot_user_id=self.user.id if self.user is not None else None,
            bot_role_ids=self._get_bot_role_ids(message),
            is_bot_mentioned=mentioned,
        )
        if prompt is None:
            self._logger.info(
                "Ignoring message channel=%s author=%s because trigger did not match or prompt was empty",
                getattr(message.channel, "id", "unknown"),
                message.author,
            )
            if self._config.discord_trigger == "mention" and mentioned:
                await send_discord_text(message, "Bot へのメンションと一緒に本文も送ってください。")
            return

        self._logger.info(
            "Executing agent for channel=%s author=%s prompt_length=%s backend=%s workspace_id=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            len(prompt.prompt),
            self._router.default_backend(),
            self._router.default_workspace(),
        )
        async with message.channel.typing():
            try:
                result = await self._router.run_prompt(prompt.prompt)
            except (RouterError, CodexError) as exc:
                self._logger.exception(
                    "Agent execution failed channel=%s author=%s",
                    getattr(message.channel, "id", "unknown"),
                    message.author,
                )
                await send_discord_text(message, f"Agent 実行エラー:\n{exc}")
                return

        delivery_mode = choose_discord_delivery_mode(message)
        self._logger.info(
            "Sending Discord response channel=%s author=%s backend=%s workspace_id=%s response_length=%s delivery_mode=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            result.backend_name,
            result.workspace_id,
            len(result.message),
            delivery_mode,
        )
        await send_discord_response(message, result.message, delivery_mode)

    def _is_trigger_mentioned(self, message: discord.Message) -> bool:
        """Bot 本体か Bot ロールへのメンションを判定する。

        Parameters
        ----------
        message : discord.Message
            判定対象メッセージ。

        Returns
        -------
        bool
            反応対象なら `True`。
        """

        if self.user is not None and self.user.mentioned_in(message):
            return True
        bot_role_ids = self._get_bot_role_ids(message)
        if not bot_role_ids:
            return False
        mentioned_role_ids = {role.id for role in message.role_mentions}
        return bool(bot_role_ids & mentioned_role_ids)

    def _get_bot_role_ids(self, message: discord.Message) -> set[int]:
        """Bot が持つ role ID 一覧を返す。

        Parameters
        ----------
        message : discord.Message
            受信メッセージ。

        Returns
        -------
        set[int]
            Bot が持つ role ID 一覧。取得できなければ空集合。
        """

        if self.user is None or message.guild is None:
            return set()

        bot_member = message.guild.get_member(self.user.id)
        if bot_member is None:
            return set()

        return {role.id for role in bot_member.roles}


DiscordAgentBridgeClient = DiscordBot
DiscordCodexBridgeClient = DiscordBot
