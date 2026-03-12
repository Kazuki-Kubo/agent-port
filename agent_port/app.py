"""アプリケーションの起動メッセージを構築するモジュール。"""

from agent_port.config import AppConfig


def build_startup_summary(config: AppConfig) -> str:
    """起動時に表示する設定サマリーを生成する。

    Parameters
    ----------
    config : AppConfig
        表示対象のアプリケーション設定。

    Returns
    -------
    str
        利用中のバックエンドと workspace を含む表示文字列。
    """

    lines = [
        "agent-port is ready.",
        f"chat_backend={config.chat_backend}",
        f"agent_backend={config.agent_backend}",
        f"agent_workspace={config.agent_workspace}",
        f"log_level={config.log_level}",
    ]
    return "\n".join(lines)


def main() -> None:
    """環境変数から設定を読み込み、起動サマリーを表示する。

    Returns
    -------
    None
        起動サマリーを標準出力へ表示した後に終了する。
    """

    config = AppConfig.from_env()
    print(build_startup_summary(config))
