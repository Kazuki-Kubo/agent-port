"""Discord と Codex CLI をつなぐ最小のブリッジ。"""

from __future__ import annotations

from dataclasses import dataclass
import logging

import discord

from agent_port.codex_runner import CodexExecutionError, CodexRunner
from agent_port.config import AppConfig

DISCORD_MESSAGE_LIMIT = 2000


@dataclass(frozen=True)
class DiscordPrompt:
    """Discord から抽出した実行対象プロンプトを保持する。

    Attributes
    ----------
    prompt : str
        Codex へ渡す本文。
    """

    prompt: str


class DiscordCodexBridgeClient(discord.Client):
    """Discord メッセージを Codex CLI へ中継するクライアント。"""

    def __init__(self, config: AppConfig, codex_runner: CodexRunner) -> None:
        """Discord クライアントを初期化する。

        Parameters
        ----------
        config : AppConfig
            実行設定。
        codex_runner : CodexRunner
            Codex 実行を担当するランナー。

        Returns
        -------
        None
            Discord へ接続するクライアントを初期化する。
        """

        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self._config = config
        self._codex_runner = codex_runner
        self._logger = logging.getLogger(__name__)

    async def on_ready(self) -> None:
        """接続完了時にログを出力する。

        Returns
        -------
        None
            接続済み Bot 名と設定済みトリガー方式をログ出力する。
        """

        if self.user is None:
            return

        self._logger.info(
            "Discord Bot connected as %s with trigger_mode %s",
            self.user,
            self._config.discord_trigger_mode,
        )

    async def on_message(self, message: discord.Message) -> None:
        """Discord メッセージを受け取って Codex 実行を行う。

        Parameters
        ----------
        message : discord.Message
            受信した Discord メッセージ。

        Returns
        -------
        None
            対象メッセージなら Codex へ中継し、応答を Discord へ返す。
        """

        if message.author.bot:
            self._logger.debug(
                "Ignoring bot message channel=%s author=%s",
                getattr(message.channel, "id", "unknown"),
                message.author,
            )
            return

        is_bot_mentioned = self.user.mentioned_in(message) if self.user is not None else False
        self._logger.info(
            "Received Discord message channel=%s author=%s trigger_mode=%s mentioned=%s content=%r",
            getattr(message.channel, "id", "unknown"),
            message.author,
            self._config.discord_trigger_mode,
            is_bot_mentioned,
            message.content,
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
                    "Botをメンションしたあとに本文も送ってください。",
                )
            return

        self._logger.info(
            "Executing Codex for channel=%s author=%s prompt_length=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            len(prompt.prompt),
        )
        async with message.channel.typing():
            try:
                result = await self._codex_runner.run_prompt(prompt.prompt)
            except CodexExecutionError as exc:
                self._logger.exception(
                    "Codex execution failed channel=%s author=%s",
                    getattr(message.channel, "id", "unknown"),
                    message.author,
                )
                await send_discord_text(message, f"Codex 実行エラー:\n{exc}")
                return

        self._logger.info(
            "Sending Discord reply channel=%s author=%s response_length=%s",
            getattr(message.channel, "id", "unknown"),
            message.author,
            len(result.message),
        )
        await send_discord_text(message, result.message)


def extract_discord_prompt(
    content: str,
    trigger_mode: str,
    bot_user_id: int | None,
    is_bot_mentioned: bool,
) -> DiscordPrompt | None:
    """Discord メッセージから Codex 実行対象の本文を取り出す。

    Parameters
    ----------
    content : str
        Discord 上のメッセージ本文。
    trigger_mode : str
        反応条件。`mention` または `all`。
    bot_user_id : int | None
        メンション判定に使う Bot ユーザー ID。
    is_bot_mentioned : bool
        Discord 側で Bot がメンションされたと判定できているかどうか。

    Returns
    -------
    DiscordPrompt | None
        対象メッセージなら抽出結果を返し、対象外なら `None` を返す。
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
    """Bot メンションを取り除いた本文を返す。

    Parameters
    ----------
    content : str
        Discord メッセージ本文。
    bot_user_id : int
        取り除き対象の Bot ユーザー ID。

    Returns
    -------
    str
        Bot メンションを除いた本文。本文が残らなければ空文字。
    """

    mention_variants = [f"<@{bot_user_id}>", f"<@!{bot_user_id}>"]
    normalized_content = content
    for mention in mention_variants:
        normalized_content = normalized_content.replace(mention, " ")
    return normalized_content.strip()


async def send_discord_text(
    message: discord.Message,
    text: str,
) -> None:
    """Discord の文字数制限に合わせて返信を分割送信する。

    Parameters
    ----------
    message : discord.Message
        返信先となる元メッセージ。
    text : str
        送信したい全文。

    Returns
    -------
    None
        文字数制限に合わせて分割しながら返信する。
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
    """Discord へ送る文字列を上限文字数で分割する。

    Parameters
    ----------
    text : str
        分割対象の文字列。
    limit : int, default=DISCORD_MESSAGE_LIMIT
        1 メッセージあたりの最大文字数。

    Returns
    -------
    list[str]
        Discord へ送信可能な文字列チャンクの配列。
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
    """上限を超える 1 行を固定長で分割する。

    Parameters
    ----------
    line : str
        分割対象の 1 行文字列。
    limit : int
        1 チャンクあたりの最大文字数。

    Returns
    -------
    list[str]
        分割済みの文字列チャンク。
    """

    chunks: list[str] = []
    for start in range(0, len(line), limit):
        chunks.append(line[start : start + limit].rstrip())
    return chunks
