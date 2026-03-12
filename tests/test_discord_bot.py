"""discord_bot と discord_io の振る舞いを検証する。"""

from pathlib import Path

import discord

from agent_port.config import AppConfig, CodexConfig
from agent_port.discord_bot import DiscordBot
from agent_port.discord_io import (
    build_discord_thread_name,
    choose_discord_delivery_mode,
    extract_discord_prompt,
    split_discord_message,
)
from agent_port.registry import AgentStore
from agent_port.router import Router
from agent_port.workspaces import Workspace, Workspaces


def test_extract_discord_prompt_strips_user_mention() -> None:
    """Bot メンションを除去して prompt を作ることを確認する。

    Returns
    -------
    None
        user mention を除いた本文だけが prompt に入る。
    """

    prompt = extract_discord_prompt(
        content="<@123> hello world",
        trigger_mode="mention",
        bot_user_id=123,
        bot_role_ids=set(),
        is_bot_mentioned=True,
    )

    assert prompt is not None
    assert prompt.prompt == "hello world"


def test_extract_discord_prompt_returns_none_without_mention() -> None:
    """mention モードでメンションがない場合は無視することを確認する。

    Returns
    -------
    None
        prompt が作られず `None` になる。
    """

    prompt = extract_discord_prompt(
        content="hello world",
        trigger_mode="mention",
        bot_user_id=123,
        bot_role_ids=set(),
        is_bot_mentioned=False,
    )

    assert prompt is None


def test_extract_discord_prompt_uses_all_mode() -> None:
    """all モードでは本文全体を prompt に使うことを確認する。

    Returns
    -------
    None
        メンションの有無に関係なく本文がそのまま入る。
    """

    prompt = extract_discord_prompt(
        content="hello world",
        trigger_mode="all",
        bot_user_id=None,
        bot_role_ids=set(),
        is_bot_mentioned=False,
    )

    assert prompt is not None
    assert prompt.prompt == "hello world"


def test_extract_discord_prompt_strips_role_mention() -> None:
    """Bot role へのメンションも prompt から除去することを確認する。

    Returns
    -------
    None
        role mention を除いた本文だけが残る。
    """

    prompt = extract_discord_prompt(
        content="<@&456> どう？",
        trigger_mode="mention",
        bot_user_id=123,
        bot_role_ids={456},
        is_bot_mentioned=True,
    )

    assert prompt is not None
    assert prompt.prompt == "どう？"


def test_split_discord_message_splits_long_text() -> None:
    """長文を Discord の上限に合わせて分割することを確認する。

    Returns
    -------
    None
        2000 文字以内の塊に分割される。
    """

    chunks = split_discord_message(text="a" * 4500, limit=2000)

    assert len(chunks) == 3
    assert all(len(chunk) <= 2000 for chunk in chunks)


def test_build_discord_thread_name_truncates() -> None:
    """スレッド名が 80 文字以内に丸められることを確認する。

    Returns
    -------
    None
        長い本文でも thread 名は 80 文字で切られる。
    """

    thread_name = build_discord_thread_name("a" * 120)

    assert len(thread_name) == 80


def test_choose_discord_delivery_mode_uses_reply_for_text_channel() -> None:
    """通常チャンネルでは reply を選ぶことを確認する。

    Returns
    -------
    None
        text channel では `reply` になる。
    """

    message = DummyMessage(
        mentioned=False,
        guild=None,
        role_mention_ids=[],
        channel=DummyChannel(discord.ChannelType.text),
    )

    assert choose_discord_delivery_mode(message) == "reply"


def test_choose_discord_delivery_mode_uses_thread_for_thread_channel() -> None:
    """スレッド内では thread を選ぶことを確認する。

    Returns
    -------
    None
        thread channel では `thread` になる。
    """

    message = DummyMessage(
        mentioned=False,
        guild=None,
        role_mention_ids=[],
        channel=DummyChannel(discord.ChannelType.public_thread),
    )

    assert choose_discord_delivery_mode(message) == "thread"


def test_is_trigger_mentioned_accepts_role_mention() -> None:
    """Bot role へのメンションも trigger として扱うことを確認する。

    Returns
    -------
    None
        Bot が持つ role に触れていれば `True` になる。
    """

    config = AppConfig(
        base_dir=Path(".").resolve(),
        chat="discord",
        default_agent="codex",
        default_workspace="sample",
        workspace_file=None,
        workspaces=Workspaces(
            [
                Workspace(
                    workspace_id="sample",
                    path=Path("..").resolve(),
                    allowed_agents=("codex",),
                )
            ]
        ),
        discord_token="token",
        discord_app_id=None,
        discord_trigger="mention",
        codex=CodexConfig(name="codex", command="codex", timeout=300),
        log_level="INFO",
    )
    client = BotForTest(config=config)
    message = DummyMessage(
        mentioned=False,
        guild=DummyGuild(bot_user_id=999, role_ids=[10, 20]),
        role_mention_ids=[20],
        channel=DummyChannel(discord.ChannelType.text),
    )

    assert client.is_trigger_mentioned(message) is True


class BotForTest:
    """`DiscordBot` の private helper を呼ぶためのラッパー。"""

    def __init__(self, config: AppConfig) -> None:
        """テスト用 client を組み立てる。

        Parameters
        ----------
        config : AppConfig
            最小構成のアプリ設定。
        """

        self._client = object.__new__(DiscordBot)
        self._client._config = config
        self._client._router = Router(
            store=AgentStore(),
            workspaces=config.workspaces,
            default_agent="codex",
            default_workspace="sample",
        )
        self._client._logger = None
        self._client._connection = DummyConnection(user=DummyUser(999))

    def is_trigger_mentioned(self, message: "DummyMessage") -> bool:
        """private helper を呼び出す。

        Parameters
        ----------
        message : DummyMessage
            テスト用の受信メッセージ。

        Returns
        -------
        bool
            trigger 判定の結果。
        """

        return self._client._is_trigger_mentioned(message)


class DummyConnection:
    """`discord.Client.user` 用の最小ダミー。"""

    def __init__(self, user: "DummyUser") -> None:
        """Bot user を保持する。

        Parameters
        ----------
        user : DummyUser
            テスト用の Bot user。
        """

        self.user = user


class DummyUser:
    """最小構成の Bot user。"""

    def __init__(self, user_id: int) -> None:
        """user ID を保持する。

        Parameters
        ----------
        user_id : int
            Bot の user ID。
        """

        self.id = user_id

    def mentioned_in(self, message: "DummyMessage") -> bool:
        """本文メンション判定を返す。

        Parameters
        ----------
        message : DummyMessage
            テスト対象メッセージ。

        Returns
        -------
        bool
            本文上のメンション有無。
        """

        return message.mentioned


class DummyRole:
    """最小構成の role。"""

    def __init__(self, role_id: int) -> None:
        """role ID を保持する。

        Parameters
        ----------
        role_id : int
            role の ID。
        """

        self.id = role_id


class DummyMember:
    """role 一覧だけを持つ member。"""

    def __init__(self, role_ids: list[int]) -> None:
        """role 一覧を保持する。

        Parameters
        ----------
        role_ids : list[int]
            Bot が持つ role ID 一覧。
        """

        self.roles = [DummyRole(role_id) for role_id in role_ids]


class DummyGuild:
    """Bot member を返せる最小構成の guild。"""

    def __init__(self, bot_user_id: int, role_ids: list[int]) -> None:
        """Bot の member 情報を保持する。

        Parameters
        ----------
        bot_user_id : int
            Bot の user ID。
        role_ids : list[int]
            Bot が持つ role ID 一覧。
        """

        self._bot_user_id = bot_user_id
        self._member = DummyMember(role_ids)

    def get_member(self, user_id: int) -> DummyMember | None:
        """Bot member を返す。

        Parameters
        ----------
        user_id : int
            取得対象の user ID。

        Returns
        -------
        DummyMember | None
            Bot 本人なら member、違えば `None`。
        """

        if user_id == self._bot_user_id:
            return self._member
        return None


class DummyChannel:
    """channel type だけを持つ最小構成の channel。"""

    def __init__(self, channel_type: discord.ChannelType) -> None:
        """channel type を保持する。

        Parameters
        ----------
        channel_type : discord.ChannelType
            テスト対象の channel type。
        """

        self.type = channel_type


class DummyMessage:
    """テストに必要な属性だけを持つメッセージ。"""

    def __init__(
        self,
        mentioned: bool,
        guild: DummyGuild | None,
        role_mention_ids: list[int],
        channel: DummyChannel,
    ) -> None:
        """メッセージ属性を保持する。

        Parameters
        ----------
        mentioned : bool
            本文メンションの有無。
        guild : DummyGuild | None
            関連 guild。
        role_mention_ids : list[int]
            メッセージ内の role mention 一覧。
        channel : DummyChannel
            投稿先 channel。
        """

        self.mentioned = mentioned
        self.guild = guild
        self.role_mentions = [DummyRole(role_id) for role_id in role_mention_ids]
        self.channel = channel
