"""Discord と Agent を中継するブリッジ。"""

from __future__ import annotations

from dataclasses import dataclass
import logging

import discord

from agent_port.agent_router import AgentRouter, AgentRouterError
from agent_port.codex_runner import CodexExecutionError
from agent_port.config import AppConfig

DISCORD_MESSAGE_LIMIT = 2000


@dataclass(frozen=True)
class DiscordPrompt:
    """Discord から取り出した実行用 prompt。

    Attributes
    ----------
    prompt : str
        Agent に渡す最終 prompt。
    """

    prompt: str


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
            "Discord Bot connected as %s with trigger_mode %s default_agent=%s",
            self.user,
            self._config.discord_trigger_mode,
            self._agent_router.get_default_backend(),
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
            "Executing agent for channel=%s author=%s prompt_length=%s backend=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            len(prompt.prompt),
            self._agent_router.get_default_backend(),
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
            "Sending Discord reply channel=%s author=%s backend=%s response_length=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            result.backend_name,
            len(result.message),
        )
        await send_discord_text(message, result.message)

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


def extract_discord_prompt(
    content: str,
    trigger_mode: str,
    bot_user_id: int | None,
    is_bot_mentioned: bool,
) -> DiscordPrompt | None:
    """Discord メッセージから Agent 用 prompt を取り出す。

    Parameters
    ----------
    content : str
        Discord の生メッセージ本文。
    trigger_mode : str
        `mention` または `all`。
    bot_user_id : int | None
        Bot ユーザー ID。
    is_bot_mentioned : bool
        受信時点で Bot か Bot ロールがメンションされたかどうか。

    Returns
    -------
    DiscordPrompt | None
        有効な prompt が得られた場合はその内容。無効なら `None`。
    """

    normalized_content = content.strip()
    if not normalized_content:
        return None

    if trigger_mode == "all":
        prompt = normalized_content
    elif trigger_mode == "mention":
        if bot_user_id is None or not is_bot_mentioned:
            return None
        prompt = _strip_bot_mention(
            content=normalized_content,
            bot_user_id=bot_user_id,
        )
    else:
        return None

    if not prompt:
        return None

    return DiscordPrompt(prompt=prompt)


def _strip_bot_mention(content: str, bot_user_id: int) -> str:
    """Bot メンションを除去した本文を返す。

    Parameters
    ----------
    content : str
        Discord メッセージ本文。
    bot_user_id : int
        Bot ユーザー ID。

    Returns
    -------
    str
        Bot メンション除去後の本文。
    """

    mention_variants = [f"<@{bot_user_id}>", f"<@!{bot_user_id}>"]
    normalized_content = content
    for mention in mention_variants:
        normalized_content = normalized_content.replace(mention, " ")
    return normalized_content.strip()


async def send_discord_text(message: discord.Message, text: str) -> None:
    """Discord の文字数制限に合わせて返信する。

    Parameters
    ----------
    message : discord.Message
        返信先となる元メッセージ。
    text : str
        返信する本文。

    Returns
    -------
    None
        必要に応じて複数チャンクに分割して返信する。
    """

    chunks = split_discord_message(text=text, limit=DISCORD_MESSAGE_LIMIT)
    logging.getLogger(__name__).info(
        "Replying to message_id=%s in channel=%s chunk_count=%s",
        getattr(message, "id", "unknown"),
        getattr(message.channel, "id", "unknown"),
        len(chunks),
    )
    for chunk in chunks:
        await message.reply(chunk, mention_author=False)


def split_discord_message(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """長文を Discord 送信可能なチャンクへ分割する。

    Parameters
    ----------
    text : str
        分割対象の本文。
    limit : int, default=DISCORD_MESSAGE_LIMIT
        1 メッセージあたりの最大文字数。

    Returns
    -------
    list[str]
        Discord へ順番に送る本文チャンク一覧。
    """

    normalized_text = text.strip()
    if not normalized_text:
        return ["(empty)"]

    chunks: list[str] = []
    current_chunk = ""
    for line in normalized_text.splitlines(keepends=True):
        if len(line) > limit:
            if current_chunk:
                chunks.append(current_chunk.rstrip())
                current_chunk = ""
            chunks.extend(_split_long_line(line=line, limit=limit))
            continue

        if len(current_chunk) + len(line) > limit:
            chunks.append(current_chunk.rstrip())
            current_chunk = line
            continue

        current_chunk += line

    if current_chunk:
        chunks.append(current_chunk.rstrip())

    return chunks


def _split_long_line(line: str, limit: int) -> list[str]:
    """長すぎる 1 行を固定長で分割する。

    Parameters
    ----------
    line : str
        分割対象の 1 行。
    limit : int
        1 チャンクあたりの最大文字数。

    Returns
    -------
    list[str]
        分割後のチャンク一覧。
    """

    chunks: list[str] = []
    for start in range(0, len(line), limit):
        chunks.append(line[start : start + limit].rstrip())
    return chunks
