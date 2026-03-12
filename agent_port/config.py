"""環境変数からアプリケーション設定を読み込むモジュール。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


class ConfigError(ValueError):
    """設定値が不正な場合に送出する例外。"""


@dataclass(frozen=True)
class AppConfig:
    """アプリケーションの実行設定を保持する。

    Attributes
    ----------
    chat_backend : str
        利用するチャット実装の識別子。
    agent_backend : str
        利用する Agent 実装の識別子。
    discord_bot_token : str | None
        Discord Bot へ接続するためのトークン。
    discord_application_id : str | None
        Discord アプリケーションの識別子。
    agent_workspace : Path
        Agent を実行する workspace の絶対パス。
    log_level : str
        ログ出力レベル。
    """

    chat_backend: str
    agent_backend: str
    discord_bot_token: str | None
    discord_application_id: str | None
    agent_workspace: Path
    log_level: str

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "AppConfig":
        """環境変数から設定を読み込む。

        Parameters
        ----------
        base_dir : Path | None, default=None
            相対パスの基準ディレクトリ。未指定時は現在の作業ディレクトリを使う。

        Returns
        -------
        AppConfig
            読み込んだ設定値を保持する設定オブジェクト。

        Raises
        ------
        ConfigError
            必須設定が不足している場合や、workspace の形式が不正な場合。
        """

        resolved_base_dir = (base_dir or Path.cwd()).resolve()
        chat_backend = os.getenv("AGENT_PORT_CHAT_BACKEND", "discord")
        agent_backend = os.getenv("AGENT_PORT_AGENT_BACKEND", "codex")
        discord_bot_token = _read_optional_env("AGENT_PORT_DISCORD_BOT_TOKEN")
        discord_application_id = _read_optional_env("AGENT_PORT_DISCORD_APPLICATION_ID")
        workspace_value = os.getenv("AGENT_PORT_AGENT_WORKSPACE", ".")
        log_level = os.getenv("AGENT_PORT_LOG_LEVEL", "INFO")

        agent_workspace = _resolve_relative_workspace(
            workspace_value=workspace_value,
            base_dir=resolved_base_dir,
        )

        if chat_backend == "discord" and not discord_bot_token:
            raise ConfigError(
                "AGENT_PORT_CHAT_BACKEND=discord の場合は "
                "AGENT_PORT_DISCORD_BOT_TOKEN が必要です。"
            )

        return cls(
            chat_backend=chat_backend,
            agent_backend=agent_backend,
            discord_bot_token=discord_bot_token,
            discord_application_id=discord_application_id,
            agent_workspace=agent_workspace,
            log_level=log_level,
        )


def _read_optional_env(name: str) -> str | None:
    """空文字を除外して環境変数を読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。

    Returns
    -------
    str | None
        値が存在し、かつ空文字でない場合はその値を返す。そうでなければ `None`。
    """

    value = os.getenv(name)
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _resolve_relative_workspace(workspace_value: str, base_dir: Path) -> Path:
    """workspace の相対パスを解決する。

    Parameters
    ----------
    workspace_value : str
        環境変数で受け取った workspace のパス文字列。
    base_dir : Path
        相対パスの基準ディレクトリ。

    Returns
    -------
    Path
        解決済みの絶対パス。

    Raises
    ------
    ConfigError
        workspace が空文字または絶対パスだった場合。
    """

    normalized_value = workspace_value.strip()
    if not normalized_value:
        raise ConfigError("AGENT_PORT_AGENT_WORKSPACE は空文字にできません。")

    workspace_path = Path(normalized_value)
    if workspace_path.is_absolute():
        raise ConfigError(
            "AGENT_PORT_AGENT_WORKSPACE は相対パスで指定してください。"
        )

    return (base_dir / workspace_path).resolve()
