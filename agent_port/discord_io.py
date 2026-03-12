"""Discord 入出力の補助関数をまとめる。"""

from __future__ import annotations

from dataclasses import dataclass
import logging

import discord

DISCORD_MESSAGE_LIMIT = 2000
THREAD_TYPES = {
    discord.ChannelType.public_thread,
    discord.ChannelType.private_thread,
    discord.ChannelType.news_thread,
}


@dataclass(frozen=True)
class DiscordPrompt:
    """Discord から抽出した prompt を表す。

    Attributes
    ----------
    prompt : str
        Agent に渡す本文。
    """

    prompt: str


def extract_discord_prompt(
    content: str,
    trigger_mode: str,
    bot_user_id: int | None,
    bot_role_ids: set[int] | None,
    is_bot_mentioned: bool,
) -> DiscordPrompt | None:
    """Discord メッセージから prompt を取り出す。

    Parameters
    ----------
    content : str
        受信本文。
    trigger_mode : str
        `mention` または `all`。
    bot_user_id : int | None
        Bot の user ID。
    bot_role_ids : set[int] | None
        Bot が持つ role ID 一覧。
    is_bot_mentioned : bool
        メンション判定結果。

    Returns
    -------
    DiscordPrompt | None
        抽出できた prompt。条件外なら `None`。
    """

    text = content.strip()
    if not text:
        return None

    if trigger_mode == "all":
        prompt = text
    elif trigger_mode == "mention":
        if bot_user_id is None or not is_bot_mentioned:
            return None
        prompt = strip_bot_mention(
            content=text,
            bot_user_id=bot_user_id,
            bot_role_ids=bot_role_ids or set(),
        )
    else:
        return None

    if not prompt:
        return None
    return DiscordPrompt(prompt=prompt)


def strip_bot_mention(
    content: str,
    bot_user_id: int,
    bot_role_ids: set[int],
) -> str:
    """Bot への mention を本文から除去する。

    Parameters
    ----------
    content : str
        元の本文。
    bot_user_id : int
        Bot の user ID。
    bot_role_ids : set[int]
        Bot が持つ role ID 一覧。

    Returns
    -------
    str
        mention 除去後の本文。
    """

    text = content
    mentions = [
        f"<@{bot_user_id}>",
        f"<@!{bot_user_id}>",
        *(f"<@&{role_id}>" for role_id in bot_role_ids),
    ]
    for mention in mentions:
        text = text.replace(mention, " ")
    return text.strip()


def choose_discord_delivery_mode(message: discord.Message) -> str:
    """Discord 返信方法を host 側で決める。

    Parameters
    ----------
    message : discord.Message
        元メッセージ。

    Returns
    -------
    str
        通常チャンネルなら `reply`、スレッドなら `thread`。
    """

    channel_type = getattr(message.channel, "type", None)
    if isinstance(message.channel, discord.Thread) or channel_type in THREAD_TYPES:
        return "thread"
    return "reply"


async def send_discord_response(
    message: discord.Message,
    text: str,
    delivery_mode: str,
) -> None:
    """返信方法に応じて Discord へ送信する。

    Parameters
    ----------
    message : discord.Message
        元メッセージ。
    text : str
        返信本文。
    delivery_mode : str
        `reply` または `thread`。

    Returns
    -------
    None
        Discord へ送信する。
    """

    if delivery_mode == "thread":
        await send_discord_thread(message, text)
        return
    await send_discord_text(message, text)


async def send_discord_text(message: discord.Message, text: str) -> None:
    """通常返信として送信する。

    Parameters
    ----------
    message : discord.Message
        元メッセージ。
    text : str
        返信本文。

    Returns
    -------
    None
        必要なら分割して返信する。
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


async def send_discord_thread(message: discord.Message, text: str) -> None:
    """同じスレッドへ送信する。

    Parameters
    ----------
    message : discord.Message
        元メッセージ。
    text : str
        返信本文。

    Returns
    -------
    None
        必要なら分割してスレッドへ送る。
    """

    target = resolve_discord_thread(message)
    chunks = split_discord_message(text=text, limit=DISCORD_MESSAGE_LIMIT)
    logging.getLogger(__name__).info(
        "Sending thread response message_id=%s channel=%s thread=%s chunk_count=%s",
        getattr(message, "id", "unknown"),
        getattr(message.channel, "id", "unknown"),
        getattr(target, "id", "unknown"),
        len(chunks),
    )
    for chunk in chunks:
        await target.send(chunk)


def resolve_discord_thread(message: discord.Message) -> discord.abc.Messageable:
    """返信先スレッドを解決する。

    Parameters
    ----------
    message : discord.Message
        元メッセージ。

    Returns
    -------
    discord.abc.Messageable
        送信先スレッド。

    Raises
    ------
    ValueError
        スレッド以外で `thread` が要求された場合。
    """

    if isinstance(message.channel, discord.Thread):
        return message.channel
    channel_type = getattr(message.channel, "type", None)
    if channel_type in THREAD_TYPES:
        return message.channel
    raise ValueError("通常チャンネルでは thread 返信を選べません。")


def build_discord_thread_name(content: str) -> str:
    """スレッド名の候補を作る。

    Parameters
    ----------
    content : str
        元メッセージ本文。

    Returns
    -------
    str
        最大 80 文字のスレッド名。
    """

    text = " ".join(content.strip().split())
    if not text:
        return "agent-port thread"
    return text[:80]


def split_discord_message(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """Discord の制限に合わせて本文を分割する。

    Parameters
    ----------
    text : str
        返信本文。
    limit : int, default=DISCORD_MESSAGE_LIMIT
        1 メッセージあたりの最大文字数。

    Returns
    -------
    list[str]
        分割後の本文一覧。
    """

    text = text.strip()
    if not text:
        return ["(empty)"]

    chunks: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(line) > limit:
            if current:
                chunks.append(current.rstrip())
                current = ""
            chunks.extend(_split_long_line(line=line, limit=limit))
            continue

        if len(current) + len(line) > limit:
            chunks.append(current.rstrip())
            current = line
            continue

        current += line

    if current:
        chunks.append(current.rstrip())
    return chunks


def _split_long_line(line: str, limit: int) -> list[str]:
    """長すぎる 1 行を分割する。

    Parameters
    ----------
    line : str
        分割対象の 1 行。
    limit : int
        1 片あたりの最大文字数。

    Returns
    -------
    list[str]
        分割後の文字列一覧。
    """

    return [line[start : start + limit].rstrip() for start in range(0, len(line), limit)]
