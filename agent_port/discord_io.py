"""Discord 用の prompt 抽出と返信制御をまとめるモジュール。"""

from __future__ import annotations

from dataclasses import dataclass
import logging

import discord

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


@dataclass(frozen=True)
class DiscordDelivery:
    """Discord 返信方法と本文を表す。

    Attributes
    ----------
    mode : str
        `reply` または `thread`。
    message : str
        ユーザーへ送る本文。
    """

    mode: str
    message: str


def extract_discord_delivery(text: str) -> DiscordDelivery:
    """Agent 応答から Discord の返信方法を抽出する。"""

    normalized_text = text.strip()
    if not normalized_text:
        return DiscordDelivery(mode="reply", message="")

    lines = normalized_text.splitlines()
    first_line = lines[0].strip().lower()
    if first_line in {"[delivery:reply]", "[delivery:thread]"}:
        mode = "thread" if "thread" in first_line else "reply"
        message = "\n".join(lines[1:]).strip()
        return DiscordDelivery(mode=mode, message=message)

    return DiscordDelivery(mode="reply", message=normalized_text)


def extract_discord_prompt(
    content: str,
    trigger_mode: str,
    bot_user_id: int | None,
    is_bot_mentioned: bool,
) -> DiscordPrompt | None:
    """Discord メッセージから Agent 用 prompt を取り出す。"""

    normalized_content = content.strip()
    if not normalized_content:
        return None

    if trigger_mode == "all":
        prompt = normalized_content
    elif trigger_mode == "mention":
        if bot_user_id is None or not is_bot_mentioned:
            return None
        prompt = strip_bot_mention(
            content=normalized_content,
            bot_user_id=bot_user_id,
        )
    else:
        return None

    if not prompt:
        return None

    return DiscordPrompt(prompt=prompt)


def strip_bot_mention(content: str, bot_user_id: int) -> str:
    """Bot メンションを除去した本文を返す。"""

    mention_variants = [f"<@{bot_user_id}>", f"<@!{bot_user_id}>"]
    normalized_content = content
    for mention in mention_variants:
        normalized_content = normalized_content.replace(mention, " ")
    return normalized_content.strip()


async def send_discord_response(
    message: discord.Message,
    text: str,
    delivery_mode: str,
) -> None:
    """返信モードに応じて Discord へ送信する。"""

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
    """Discord の文字数制限に合わせて返信する。"""

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
    """スレッドへ応答を送信する。"""

    target_channel = await resolve_discord_thread(message)
    chunks = split_discord_message(text=text, limit=DISCORD_MESSAGE_LIMIT)
    logging.getLogger(__name__).info(
        "Sending thread response message_id=%s channel=%s thread=%s chunk_count=%s",
        getattr(message, "id", "unknown"),
        getattr(message.channel, "id", "unknown"),
        getattr(target_channel, "id", "unknown"),
        len(chunks),
    )
    for chunk in chunks:
        await target_channel.send(chunk)


async def resolve_discord_thread(message: discord.Message) -> discord.abc.Messageable:
    """応答先のスレッドを解決する。"""

    if isinstance(message.channel, discord.Thread):
        return message.channel
    return await message.create_thread(name=build_discord_thread_name(message.content))


def build_discord_thread_name(content: str) -> str:
    """スレッド作成時に使うタイトルを組み立てる。"""

    normalized_content = " ".join(content.strip().split())
    if not normalized_content:
        return "agent-port thread"
    return normalized_content[:80]


def split_discord_message(text: str, limit: int = DISCORD_MESSAGE_LIMIT) -> list[str]:
    """長文を Discord 送信可能なチャンクへ分割する。"""

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
    """長すぎる 1 行を固定長で分割する。"""

    chunks: list[str] = []
    for start in range(0, len(line), limit):
        chunks.append(line[start : start + limit].rstrip())
    return chunks
