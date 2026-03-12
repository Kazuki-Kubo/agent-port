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
    discord_command_prefix : str
        Discord 上で Codex 実行を開始するコマンド接頭辞。
    agent_workspace : Path
        Agent を実行する workspace の絶対パス。
    codex_command : str
        実行する Codex CLI コマンド名。
    codex_timeout_seconds : int
        Codex 実行のタイムアウト秒数。
    log_level : str
        ログ出力レベル。
    """

    chat_backend: str
    agent_backend: str
    discord_bot_token: str | None
    discord_application_id: str | None
    discord_command_prefix: str
    agent_workspace: Path
    codex_command: str
    codex_timeout_seconds: int
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
            必須設定が不足している場合や、設定形式が不正な場合。
        """

        resolved_base_dir = (base_dir or Path.cwd()).resolve()
        load_dotenv_file(base_dir=resolved_base_dir)
        chat_backend = os.getenv("AGENT_PORT_CHAT_BACKEND", "discord")
        agent_backend = os.getenv("AGENT_PORT_AGENT_BACKEND", "codex")
        discord_bot_token = _read_optional_env("AGENT_PORT_DISCORD_BOT_TOKEN")
        discord_application_id = _read_optional_env("AGENT_PORT_DISCORD_APPLICATION_ID")
        discord_command_prefix = os.getenv(
            "AGENT_PORT_DISCORD_COMMAND_PREFIX",
            "!codex",
        ).strip()
        workspace_value = os.getenv("AGENT_PORT_AGENT_WORKSPACE", ".")
        codex_command = os.getenv("AGENT_PORT_CODEX_COMMAND", "codex").strip()
        codex_timeout_seconds = _read_positive_int_env(
            name="AGENT_PORT_CODEX_TIMEOUT_SECONDS",
            default=300,
        )
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
        if not discord_command_prefix:
            raise ConfigError(
                "AGENT_PORT_DISCORD_COMMAND_PREFIX は空文字にできません。"
            )
        if not codex_command:
            raise ConfigError("AGENT_PORT_CODEX_COMMAND は空文字にできません。")

        return cls(
            chat_backend=chat_backend,
            agent_backend=agent_backend,
            discord_bot_token=discord_bot_token,
            discord_application_id=discord_application_id,
            discord_command_prefix=discord_command_prefix,
            agent_workspace=agent_workspace,
            codex_command=codex_command,
            codex_timeout_seconds=codex_timeout_seconds,
            log_level=log_level,
        )


def load_dotenv_file(base_dir: Path) -> None:
    """基準ディレクトリ直下の `.env` を読み込み、未設定の環境変数へ反映する。

    Parameters
    ----------
    base_dir : Path
        `.env` を探索する基準ディレクトリ。

    Returns
    -------
    None
        `.env` が存在する場合のみ、未設定の環境変数を補完する。
    """

    dotenv_path = base_dir / ".env"
    if not dotenv_path.exists():
        return

    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        normalized_line = line.strip()
        if not normalized_line or normalized_line.startswith("#"):
            continue
        if "=" not in normalized_line:
            continue

        key, value = normalized_line.split("=", 1)
        env_name = key.strip()
        if not env_name:
            continue

        os.environ.setdefault(env_name, value.strip())


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


def _read_positive_int_env(name: str, default: int) -> int:
    """正の整数として環境変数を読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : int
        値が未指定だった場合の既定値。

    Returns
    -------
    int
        読み込んだ正の整数値。

    Raises
    ------
    ConfigError
        整数へ変換できない場合や、1 未満だった場合。
    """

    raw_value = os.getenv(name)
    if raw_value is None:
        return default

    try:
        parsed_value = int(raw_value)
    except ValueError as exc:
        raise ConfigError(f"{name} は整数で指定してください。") from exc

    if parsed_value < 1:
        raise ConfigError(f"{name} は 1 以上で指定してください。")

    return parsed_value


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
