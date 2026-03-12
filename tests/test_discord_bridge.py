"""discord_bridge モジュールの振る舞いを検証するテスト。"""

from agent_port.discord_bridge import extract_discord_prompt, split_discord_message


def test_extract_discord_prompt_returns_prompt_for_prefixed_message() -> None:
    """接頭辞付きメッセージから実行本文を抽出できることを確認する。

    Returns
    -------
    None
        接頭辞を除いた本文が取り出されることを検証する。
    """

    prompt = extract_discord_prompt(content="!codex hello world", prefix="!codex")

    assert prompt is not None
    assert prompt.prompt == "hello world"


def test_extract_discord_prompt_returns_none_for_non_target_message() -> None:
    """対象外メッセージは無視されることを確認する。

    Returns
    -------
    None
        接頭辞がない場合に `None` が返ることを検証する。
    """

    prompt = extract_discord_prompt(content="hello world", prefix="!codex")

    assert prompt is None


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
