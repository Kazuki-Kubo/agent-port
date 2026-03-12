"""discord_bot と discord_io の補助処理を確認する。"""

from pathlib import Path

from agent_port.config import AppConfig, CodexConfig
from agent_port.discord_bot import DiscordBot
from agent_port.discord_io import (
    build_discord_thread_name,
    extract_discord_delivery,
    extract_discord_prompt,
    split_discord_message,
)
from agent_port.registry import AgentRegistry
from agent_port.router import AgentRouter
from agent_port.workspaces import ManagedWorkspace, WorkspaceRegistry


def test_extract_discord_prompt_strips_leading_mention() -> None:
    """先頭メンションを外して prompt を作ることを確認する。

    Returns
    -------
    None
        Bot メンションを除いた本文が得られることを確認する。
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
    """mention モードでメンションがないと無視することを確認する。

    Returns
    -------
    None
        `None` が返ることを確認する。
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
    """all モードでは本文全体を使うことを確認する。

    Returns
    -------
    None
        本文がそのまま prompt になることを確認する。
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


def test_extract_discord_prompt_accepts_mid_mention() -> None:
    """本文中のメンションでも受け付けることを確認する。

    Returns
    -------
    None
        メンション位置に依存しないことを確認する。
    """

    prompt = extract_discord_prompt(
        content="hello <@123> world",
        trigger_mode="mention",
        bot_user_id=123,
        bot_role_ids=set(),
        is_bot_mentioned=True,
    )

    assert prompt is not None
    assert "hello" in prompt.prompt
    assert "world" in prompt.prompt


def test_split_discord_message_splits_long_text() -> None:
    """長文が分割されることを確認する。

    Returns
    -------
    None
        Discord の文字数制限を超えないことを確認する。
    """

    chunks = split_discord_message(text="a" * 4500, limit=2000)

    assert len(chunks) == 3
    assert all(len(chunk) <= 2000 for chunk in chunks)


def test_extract_discord_prompt_strips_role_mention() -> None:
    """Bot role のメンションも prompt から除去することを確認する。

    Returns
    -------
    None
        role mention を含まない本文だけが残ることを確認する。
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


def test_extract_discord_delivery_reads_thread_directive() -> None:
    """配送制御行から thread を読めることを確認する。

    Returns
    -------
    None
        mode と本文が正しく分かれることを確認する。
    """

    delivery = extract_discord_delivery("[delivery:thread]\n詳細はスレッドで返します。")

    assert delivery.mode == "thread"
    assert delivery.message == "詳細はスレッドで返します。"


def test_extract_discord_delivery_defaults_to_reply() -> None:
    """制御行がなければ reply 扱いになることを確認する。

    Returns
    -------
    None
        mode が `reply` になることを確認する。
    """

    delivery = extract_discord_delivery("通常の返信です。")

    assert delivery.mode == "reply"
    assert delivery.message == "通常の返信です。"


def test_build_discord_thread_name_truncates() -> None:
    """スレッド名が 80 文字以内になることを確認する。

    Returns
    -------
    None
        長文でも 80 文字に切られることを確認する。
    """

    thread_name = build_discord_thread_name("a" * 120)

    assert len(thread_name) == 80


def test_is_trigger_mentioned_accepts_role_mention() -> None:
    """Bot ロールへのメンションでも反応することを確認する。

    Returns
    -------
    None
        ロール ID が一致すると `True` になることを確認する。
    """

    config = AppConfig(
        base_dir=Path(".").resolve(),
        chat="discord",
        default_agent="codex",
        default_workspace="sample",
        workspace_file=None,
        workspaces=WorkspaceRegistry(
            [
                ManagedWorkspace(
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
    )

    assert client.is_trigger_mentioned(message) is True


class BotForTest:
    """`_is_trigger_mentioned` を呼ぶためのラッパー。"""

    def __init__(self, config: AppConfig) -> None:
        """テスト用 client を組み立てる。

        Parameters
        ----------
        config : AppConfig
            利用する設定。
        """

        workspaces = config.workspaces
        self._client = object.__new__(DiscordBot)
        self._client._config = config
        self._client._router = AgentRouter(
            registry=AgentRegistry(),
            workspace_registry=workspaces,
            default_backend="codex",
            default_workspace_id="sample",
        )
        self._client._logger = None
        self._client._connection = DummyConnection(user=DummyUser(999))

    def is_trigger_mentioned(self, message: "DummyMessage") -> bool:
        """private メソッドを呼び出す。

        Parameters
        ----------
        message : DummyMessage
            テスト用メッセージ。

        Returns
        -------
        bool
            判定結果。
        """

        return self._client._is_trigger_mentioned(message)


class DummyConnection:
    """`discord.Client.user` 用のダミー接続。"""

    def __init__(self, user: "DummyUser") -> None:
        """user を保持する。

        Parameters
        ----------
        user : DummyUser
            Bot ユーザー。
        """

        self.user = user


class DummyUser:
    """最小限の Bot ユーザー。"""

    def __init__(self, user_id: int) -> None:
        """ユーザー ID を保持する。

        Parameters
        ----------
        user_id : int
            user ID。
        """

        self.id = user_id

    def mentioned_in(self, message: "DummyMessage") -> bool:
        """本文メンション判定を返す。

        Parameters
        ----------
        message : DummyMessage
            判定対象メッセージ。

        Returns
        -------
        bool
            メッセージ側の判定値。
        """

        return message.mentioned


class DummyRole:
    """最小限の role。"""

    def __init__(self, role_id: int) -> None:
        """role ID を保持する。

        Parameters
        ----------
        role_id : int
            role ID。
        """

        self.id = role_id


class DummyMember:
    """role 一覧だけを持つ member。"""

    def __init__(self, role_ids: list[int]) -> None:
        """role 一覧を作る。

        Parameters
        ----------
        role_ids : list[int]
            role ID 一覧。
        """

        self.roles = [DummyRole(role_id) for role_id in role_ids]


class DummyGuild:
    """member 取得だけを持つ guild。"""

    def __init__(self, bot_user_id: int, role_ids: list[int]) -> None:
        """Bot 情報を保持する。

        Parameters
        ----------
        bot_user_id : int
            Bot user ID。
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
            取得する user ID。

        Returns
        -------
        DummyMember | None
            一致時は member、それ以外は `None`。
        """

        if user_id == self._bot_user_id:
            return self._member
        return None


class DummyMessage:
    """判定に必要な最小限のメッセージ。"""

    def __init__(
        self,
        mentioned: bool,
        guild: DummyGuild | None,
        role_mention_ids: list[int],
    ) -> None:
        """メッセージ属性を保持する。

        Parameters
        ----------
        mentioned : bool
            本文メンション判定。
        guild : DummyGuild | None
            所属 guild。
        role_mention_ids : list[int]
            メッセージ中の role メンション一覧。
        """

        self.mentioned = mentioned
        self.guild = guild
        self.role_mentions = [DummyRole(role_id) for role_id in role_mention_ids]
