"""discord_bridge モジュールの振る舞いを検証するテスト。"""

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
