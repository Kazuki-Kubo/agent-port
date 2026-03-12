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
            接続済み Bot 名と設定済み prefix をログ出力する。
        """

        if self.user is None:
            return

        self._logger.info(
            "Discord Bot connected as %s with prefix %s",
            self.user,
            self._config.discord_command_prefix,
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
            return

        prompt = extract_discord_prompt(
            content=message.content,
            prefix=self._config.discord_command_prefix,
        )
        if prompt is None:
            return

        async with message.channel.typing():
            try:
                result = await self._codex_runner.run_prompt(prompt.prompt)
            except CodexExecutionError as exc:
                await send_discord_text(message, f"Codex 実行エラー:\n{exc}")
                return

        await send_discord_text(message, result.message)


def extract_discord_prompt(content: str, prefix: str) -> DiscordPrompt | None:
    """Discord メッセージから Codex 実行対象の本文を取り出す。

    Parameters
    ----------
    content : str
        Discord 上のメッセージ本文。
    prefix : str
        実行トリガーとなる接頭辞。

    Returns
    -------
    DiscordPrompt | None
        対象メッセージなら抽出結果を返し、対象外なら `None` を返す。
    """

    normalized_content = content.strip()
    if not normalized_content.startswith(prefix):
        return None

    prompt = normalized_content[len(prefix) :].strip()
    if not prompt:
        return None

    return DiscordPrompt(prompt=prompt)


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

    for chunk in split_discord_message(text=text, limit=DISCORD_MESSAGE_LIMIT):
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
