"""CLI で表示する挨拶メッセージを提供するモジュール。"""


def build_greeting(app_name: str = "agent-port") -> str:
    """表示用の挨拶メッセージを生成する。

    Parameters
    ----------
    app_name : str, default="agent-port"
        メッセージ内に含めるアプリケーション名。

    Returns
    -------
    str
        画面表示用に整形された挨拶メッセージ。
    """

    return f"Hello from {app_name}!"


def main() -> None:
    """CLI の標準出力へ挨拶メッセージを表示する。

    Returns
    -------
    None
        標準出力へメッセージを表示した後に終了する。
    """

    print(build_greeting())


if __name__ == "__main__":
    main()
