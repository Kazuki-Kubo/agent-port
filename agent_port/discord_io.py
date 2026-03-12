"""Discord 入出力の補助関数をまとめる。"""

from __future__ import annotations

from dataclasses import dataclass
import logging

import discord

DISCORD_MESSAGE_LIMIT = 2000


@dataclass(frozen=True)
class DiscordPrompt:
    """Discord から抽出した prompt を表す。

    Attributes
    ----------
    prompt : str
        Agent に渡す本文。
    """

    prompt: str


@dataclass(frozen=True)
class DiscordDelivery:
    """Discord への返信方法を表す。

    Attributes
    ----------
    mode : str
        `reply` または `thread`。
    message : str
        返信本文。
    """

    mode: str
    message: str


def extract_discord_delivery(text: str) -> DiscordDelivery:
    """返信方法の制御行を解釈する。

    Parameters
    ----------
    text : str
        Agent から返された本文。

    Returns
    -------
    DiscordDelivery
        返信方法と本文。
    """

    text = text.strip()
    if not text:
        return DiscordDelivery(mode="reply", message="")

    lines = text.splitlines()
    first_line = lines[0].strip().lower()
    if first_line in {"[delivery:reply]", "[delivery:thread]"}:
        mode = "thread" if "thread" in first_line else "reply"
        return DiscordDelivery(mode=mode, message="\n".join(lines[1:]).strip())

    return DiscordDelivery(mode="reply", message=text)


def extract_discord_prompt(
    content: str,
    trigger_mode: str,
    bot_user_id: int | None,
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
        prompt = strip_bot_mention(content=text, bot_user_id=bot_user_id)
    else:
        return None

    if not prompt:
        return None
    return DiscordPrompt(prompt=prompt)


def strip_bot_mention(content: str, bot_user_id: int) -> str:
    """Bot メンションを本文から除去する。

    Parameters
    ----------
    content : str
        元の本文。
    bot_user_id : int
        Bot の user ID。

    Returns
    -------
    str
        メンション除去後の本文。
    """

    text = content
    for mention in (f"<@{bot_user_id}>", f"<@!{bot_user_id}>"):
        text = text.replace(mention, " ")
    return text.strip()


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

    if delivery_mode != "thread":
        await send_discord_text(message, text)
        return

    try:
        await send_discord_thread(message, text)
    except (discord.HTTPException, AttributeError):
        logging.getLogger(__name__).exception(
            "Failed to send thread response; falling back to reply channel=%s message_id=%s",
            getattr(message.channel, "id", "unknown"),
            getattr(message, "id", "unknown"),
        )
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
    """スレッドへ送信する。

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

    target = await resolve_discord_thread(message)
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


async def resolve_discord_thread(message: discord.Message) -> discord.abc.Messageable:
    """返信先スレッドを解決する。

    Parameters
    ----------
    message : discord.Message
        元メッセージ。

    Returns
    -------
    discord.abc.Messageable
        送信先スレッド。
    """

    if isinstance(message.channel, discord.Thread):
        return message.channel
    return await message.create_thread(name=build_discord_thread_name(message.content))


def build_discord_thread_name(content: str) -> str:
    """スレッド名を作る。

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
