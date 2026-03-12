"""discord_bridge モジュールの振る舞いを検証するテスト。"""

from pathlib import Path

from agent_port.codex_runner import CodexRunner
from agent_port.config import AppConfig
from agent_port.discord_bridge import extract_discord_prompt, split_discord_message


def test_extract_discord_prompt_returns_prompt_for_leading_mention() -> None:
    """先頭メンション付きメッセージから本文を抽出できることを確認する。

    Returns
    -------
    None
        メンションを除いた本文が取り出されることを検証する。
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
    """メンション必須モードでメンションがなければ無視することを確認する。

    Returns
    -------
    None
        対象外メッセージとして `None` が返ることを検証する。
    """

    prompt = extract_discord_prompt(
        content="hello world",
        trigger_mode="mention",
        bot_user_id=123,
        is_bot_mentioned=False,
    )

    assert prompt is None


def test_extract_discord_prompt_returns_full_text_in_all_mode() -> None:
    """全メッセージ反応モードでは本文全体を返すことを確認する。

    Returns
    -------
    None
        先頭加工なしで本文全体が返ることを検証する。
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
    """メンションが文中にあっても本文を抽出できることを確認する。

    Returns
    -------
    None
        文中メンションを除いた本文が返ることを検証する。
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
    """長文が Discord 上限以内の複数チャンクへ分割されることを確認する。

    Returns
    -------
    None
        全チャンクが上限以下であり、複数要素に分割されることを検証する。
    """

    chunks = split_discord_message(text="a" * 4500, limit=2000)

    assert len(chunks) == 3
    assert all(len(chunk) <= 2000 for chunk in chunks)


def test_is_trigger_mentioned_returns_true_for_bot_role_mention() -> None:
    """Bot が持つロールへのメンションでも反応対象になることを確認する。

    Returns
    -------
    None
        Bot 本体がメンションされていなくても、Bot ロールがメンションされていれば `True` になることを検証する。
    """

    config = AppConfig(
        chat_backend="discord",
        agent_backend="codex",
        discord_bot_token="token",
        discord_application_id=None,
        discord_trigger_mode="mention",
        agent_workspace=Path(".").resolve(),
        codex_command="codex",
        codex_timeout_seconds=300,
        log_level="INFO",
    )
    client = DiscordCodexBridgeClientForTest(config=config)

    message = DummyMessage(
        mentioned=False,
        guild=DummyGuild(bot_user_id=999, role_ids=[10, 20]),
        role_mention_ids=[20],
    )

    assert client.is_trigger_mentioned_for_test(message) is True


class DiscordCodexBridgeClientForTest:
    """判定ロジックだけをテストするための簡易ラッパー。"""

    def __init__(self, config: AppConfig) -> None:
        """テスト用ラッパーを初期化する。

        Parameters
        ----------
        config : AppConfig
            ダミーの設定値。

        Returns
        -------
        None
            必要最小限の状態だけを保持する。
        """

        from agent_port.discord_bridge import DiscordCodexBridgeClient

        self._client = object.__new__(DiscordCodexBridgeClient)
        self._client._config = config
        self._client._codex_runner = CodexRunner(config)
        self._client._logger = None
        self._client._connection = DummyConnection(user=DummyUser(999))

    def is_trigger_mentioned_for_test(self, message: "DummyMessage") -> bool:
        """内部判定関数をテスト用に呼び出す。

        Parameters
        ----------
        message : DummyMessage
            判定対象のダミーメッセージ。

        Returns
        -------
        bool
            内部判定結果。
        """

        return self._client._is_trigger_mentioned(message)


class DummyConnection:
    """discord.Client の内部 user 参照だけを満たすダミー接続。"""

    def __init__(self, user: "DummyUser") -> None:
        """ダミー接続を初期化する。

        Parameters
        ----------
        user : DummyUser
            ダミー Bot ユーザー。

        Returns
        -------
        None
            user 参照だけを保持する。
        """

        self.user = user


class DummyUser:
    """ユーザーメンション判定だけを持つダミー Bot ユーザー。"""

    def __init__(self, user_id: int) -> None:
        """ダミーユーザーを初期化する。

        Parameters
        ----------
        user_id : int
            ダミー Bot のユーザー ID。

        Returns
        -------
        None
            ID を保持する。
        """

        self.id = user_id

    def mentioned_in(self, message: "DummyMessage") -> bool:
        """メッセージ内でのユーザーメンション有無を返す。

        Parameters
        ----------
        message : DummyMessage
            判定対象メッセージ。

        Returns
        -------
        bool
            ダミーメッセージが保持する判定値。
        """

        return message.mentioned


class DummyRole:
    """ロール ID だけを持つダミーロール。"""

    def __init__(self, role_id: int) -> None:
        """ダミーロールを初期化する。

        Parameters
        ----------
        role_id : int
            ロール ID。

        Returns
        -------
        None
            ID を保持する。
        """

        self.id = role_id


class DummyMember:
    """保持ロール一覧だけを持つダミーメンバー。"""

    def __init__(self, role_ids: list[int]) -> None:
        """ダミーメンバーを初期化する。

        Parameters
        ----------
        role_ids : list[int]
            メンバーが持つロール ID 一覧。

        Returns
        -------
        None
            ダミーロールの一覧を保持する。
        """

        self.roles = [DummyRole(role_id) for role_id in role_ids]


class DummyGuild:
    """Bot メンバー取得だけを持つダミーギルド。"""

    def __init__(self, bot_user_id: int, role_ids: list[int]) -> None:
        """ダミーギルドを初期化する。

        Parameters
        ----------
        bot_user_id : int
            Bot ユーザー ID。
        role_ids : list[int]
            Bot が持つロール ID 一覧。

        Returns
        -------
        None
            Bot メンバー取得用の状態を保持する。
        """

        self._bot_user_id = bot_user_id
        self._member = DummyMember(role_ids)

    def get_member(self, user_id: int) -> DummyMember | None:
        """Bot ユーザー ID に一致した場合だけダミーメンバーを返す。

        Parameters
        ----------
        user_id : int
            取得対象のユーザー ID。

        Returns
        -------
        DummyMember | None
            Bot 自身ならダミーメンバーを返し、それ以外は `None`。
        """

        if user_id == self._bot_user_id:
            return self._member
        return None


class DummyMessage:
    """判定に必要な最小属性だけを持つダミーメッセージ。"""

    def __init__(
        self,
        mentioned: bool,
        guild: DummyGuild | None,
        role_mention_ids: list[int],
    ) -> None:
        """ダミーメッセージを初期化する。

        Parameters
        ----------
        mentioned : bool
            Bot 本体がメンションされているかどうか。
        guild : DummyGuild | None
            所属ギルド。
        role_mention_ids : list[int]
            メッセージに含まれるロールメンション ID 一覧。

        Returns
        -------
        None
            判定に必要な状態を保持する。
        """

        self.mentioned = mentioned
        self.guild = guild
        self.role_mentions = [DummyRole(role_id) for role_id in role_mention_ids]
