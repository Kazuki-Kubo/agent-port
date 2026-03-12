"""main モジュールの振る舞いを検証するテスト。"""

from main import build_greeting


def test_build_greeting_returns_default_message() -> None:
    """既定のアプリ名で挨拶文を生成できることを確認する。

    Returns
    -------
    None
        期待する文字列と一致することを検証する。
    """

    assert build_greeting() == "Hello from agent-port!"
