"""discord_bridge モジュールの振る舞いを検証するテスト。"""

from pathlib import Path

from agent_port.agent_registry import AgentRegistry
from agent_port.agent_router import AgentRouter
from agent_port.config import AppConfig, CodexAgentConfig
from agent_port.discord_bridge import (
    DiscordAgentBridgeClient,
    build_discord_thread_name,
    extract_discord_delivery,
    extract_discord_prompt,
    split_discord_message,
)


def test_extract_discord_prompt_returns_prompt_for_leading_mention() -> None:
    """先頭メンション付き本文を prompt として抽出できることを検証する。

    Returns
    -------
    None
        Bot メンション除去後の本文だけが残ることを確認する。
    """

    prompt = extract_discord_prompt(
        content="<@123> hello world",
        trigger_mode="mention",
        bot_user_id=123,
        is_bot_mentioned=True,
    )

    assert prompt is not None
    assert prompt.prompt == "hello world"


def test_extract_discord_prompt_returns_none_when_mention_mode_has_no_mention() -> None:
    """mention モードでメンションがない場合は無視することを検証する。

    Returns
    -------
    None
        `None` が返ることを確認する。
    """

    prompt = extract_discord_prompt(
        content="hello world",
        trigger_mode="mention",
        bot_user_id=123,
        is_bot_mentioned=False,
    )

    assert prompt is None


def test_extract_discord_prompt_returns_full_text_in_all_mode() -> None:
    """all モードでは本文全体を prompt として扱うことを検証する。

    Returns
    -------
    None
        メンション有無に関係なく本文が返ることを確認する。
    """

    prompt = extract_discord_prompt(
        content="hello world",
        trigger_mode="all",
        bot_user_id=None,
        is_bot_mentioned=False,
    )

    assert prompt is not None
    assert prompt.prompt == "hello world"


def test_extract_discord_prompt_accepts_mention_not_at_start() -> None:
    """本文途中のメンションでも prompt を抽出できることを検証する。

    Returns
    -------
    None
        メンション位置に依存せず本文が残ることを確認する。
    """

    prompt = extract_discord_prompt(
        content="hello <@123> world",
        trigger_mode="mention",
        bot_user_id=123,
        is_bot_mentioned=True,
    )

    assert prompt is not None
    assert "hello" in prompt.prompt
    assert "world" in prompt.prompt


def test_split_discord_message_splits_long_text_into_chunks() -> None:
    """長文が Discord 制限以下のチャンクへ分割されることを検証する。

    Returns
    -------
    None
        すべてのチャンクが制限以下になることを確認する。
    """

    chunks = split_discord_message(text="a" * 4500, limit=2000)

    assert len(chunks) == 3
    assert all(len(chunk) <= 2000 for chunk in chunks)


def test_extract_discord_delivery_reads_thread_directive() -> None:
    """Agent の配送指示から thread モードを抽出できることを検証する。

    Returns
    -------
    None
        制御行を除いた本文と thread モードが得られることを確認する。
    """

    delivery = extract_discord_delivery("[delivery:thread]\n詳細はスレッドで返します。")

    assert delivery.mode == "thread"
    assert delivery.message == "詳細はスレッドで返します。"


def test_extract_discord_delivery_defaults_to_reply_without_directive() -> None:
    """制御行がない場合は通常返信へフォールバックすることを検証する。

    Returns
    -------
    None
        mode が `reply` になり、本文がそのまま残ることを確認する。
    """

    delivery = extract_discord_delivery("通常の返答です。")

    assert delivery.mode == "reply"
    assert delivery.message == "通常の返答です。"


def test_build_discord_thread_name_truncates_long_content() -> None:
    """長い本文から Discord 用の短いスレッド名を作ることを検証する。

    Returns
    -------
    None
        スレッド名が 80 文字以下に収まることを確認する。
    """

    thread_name = build_discord_thread_name("a" * 120)

    assert len(thread_name) == 80


def test_is_trigger_mentioned_returns_true_for_bot_role_mention() -> None:
    """Bot ロールメンションでも trigger 判定が真になることを検証する。

    Returns
    -------
    None
        Bot 本体が未メンションでも Bot ロールが含まれれば `True` になることを確認する。
    """

    config = AppConfig(
        chat_backend="discord",
        default_agent_backend="codex",
        discord_bot_token="token",
        discord_application_id=None,
        discord_trigger_mode="mention",
        codex_config=CodexAgentConfig(
            backend_name="codex",
            workspace=Path(".").resolve(),
            command="codex",
            timeout_seconds=300,
        ),
        log_level="INFO",
    )
    client = DiscordAgentBridgeClientForTest(config=config)

    message = DummyMessage(
        mentioned=False,
        guild=DummyGuild(bot_user_id=999, role_ids=[10, 20]),
        role_mention_ids=[20],
    )

    assert client.is_trigger_mentioned_for_test(message) is True


class DiscordAgentBridgeClientForTest:
    """`_is_trigger_mentioned` を直接検証するためのテスト用ラッパー。"""

    def __init__(self, config: AppConfig) -> None:
        """Discord bridge の最小状態を構築する。

        Parameters
        ----------
        config : AppConfig
            テスト用設定。

        Returns
        -------
        None
            private メソッド呼び出しに必要な状態だけを埋める。
        """

        self._client = object.__new__(DiscordAgentBridgeClient)
        self._client._config = config
        self._client._agent_router = AgentRouter(
            registry=AgentRegistry(),
            default_backend="codex",
        )
        self._client._logger = None
        self._client._connection = DummyConnection(user=DummyUser(999))

    def is_trigger_mentioned_for_test(self, message: "DummyMessage") -> bool:
        """内部判定メソッドを呼び出す。

        Parameters
        ----------
        message : DummyMessage
            判定対象のテスト用メッセージ。

        Returns
        -------
        bool
            内部判定結果。
        """

        return self._client._is_trigger_mentioned(message)


class DummyConnection:
    """`discord.Client.user` 解決用のダミー接続。"""

    def __init__(self, user: "DummyUser") -> None:
        """ダミー user を保持する。

        Parameters
        ----------
        user : DummyUser
            テスト用 Bot user。

        Returns
        -------
        None
            user 属性へ保存する。
        """

        self.user = user


class DummyUser:
    """最小限の Bot user 振る舞いを持つダミー。"""

    def __init__(self, user_id: int) -> None:
        """ユーザー ID を保持する。

        Parameters
        ----------
        user_id : int
            テスト用 user ID。

        Returns
        -------
        None
            ID を保存する。
        """

        self.id = user_id

    def mentioned_in(self, message: "DummyMessage") -> bool:
        """本文中のメンション判定結果を返す。

        Parameters
        ----------
        message : DummyMessage
            判定対象のメッセージ。

        Returns
        -------
        bool
            ダミー message が保持するメンション判定。
        """

        return message.mentioned


class DummyRole:
    """ロール ID だけを持つダミー role。"""

    def __init__(self, role_id: int) -> None:
        """ロール ID を保持する。

        Parameters
        ----------
        role_id : int
            テスト用ロール ID。

        Returns
        -------
        None
            ID を保存する。
        """

        self.id = role_id


class DummyMember:
    """Bot が持つロール一覧を表すダミー member。"""

    def __init__(self, role_ids: list[int]) -> None:
        """ロール ID 一覧を role オブジェクトへ変換する。

        Parameters
        ----------
        role_ids : list[int]
            Bot が持つロール ID 一覧。

        Returns
        -------
        None
            role 属性へ保存する。
        """

        self.roles = [DummyRole(role_id) for role_id in role_ids]


class DummyGuild:
    """Bot member を返すだけのダミー guild。"""

    def __init__(self, bot_user_id: int, role_ids: list[int]) -> None:
        """Bot user と member 情報を保持する。

        Parameters
        ----------
        bot_user_id : int
            Bot user ID。
        role_ids : list[int]
            Bot が持つロール ID 一覧。

        Returns
        -------
        None
            guild 内の Bot 情報を保存する。
        """

        self._bot_user_id = bot_user_id
        self._member = DummyMember(role_ids)

    def get_member(self, user_id: int) -> DummyMember | None:
        """指定 user が Bot の場合だけ member を返す。

        Parameters
        ----------
        user_id : int
            参照対象の user ID。

        Returns
        -------
        DummyMember | None
            Bot user に一致すれば member、違えば `None`。
        """

        if user_id == self._bot_user_id:
            return self._member
        return None


class DummyMessage:
    """trigger 判定に必要な属性だけを持つダミーメッセージ。"""

    def __init__(
        self,
        mentioned: bool,
        guild: DummyGuild | None,
        role_mention_ids: list[int],
    ) -> None:
        """テスト用メッセージ状態を保持する。

        Parameters
        ----------
        mentioned : bool
            Bot 本体メンション判定。
        guild : DummyGuild | None
            所属 guild。
        role_mention_ids : list[int]
            本文に含まれるロールメンション ID 一覧。

        Returns
        -------
        None
            trigger 判定用の属性を保存する。
        """

        self.mentioned = mentioned
        self.guild = guild
        self.role_mentions = [DummyRole(role_id) for role_id in role_mention_ids]
