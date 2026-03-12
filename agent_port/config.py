"""環境変数からアプリケーション設定を読み込むモジュール。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os


class ConfigError(ValueError):
    """設定値が不正な場合に送出する例外。"""


@dataclass(frozen=True)
class AgentBackendConfig:
    """Agent 単位の共通設定を保持する。

    Attributes
    ----------
    backend_name : str
        Agent backend の識別子。
    workspace : Path
        Agent を実行する workspace の絶対パス。
    """

    backend_name: str
    workspace: Path


@dataclass(frozen=True)
class CodexAgentConfig(AgentBackendConfig):
    """Codex backend 固有の設定を保持する。

    Attributes
    ----------
    backend_name : str
        Agent backend の識別子。常に `codex`。
    workspace : Path
        Codex を実行する workspace の絶対パス。
    command : str
        実行する Codex CLI コマンド名。
    timeout_seconds : int
        Codex 実行のタイムアウト秒数。
    """

    command: str
    timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    """アプリケーションの実行設定を保持する。

    Attributes
    ----------
    chat_backend : str
        利用するチャット実装の識別子。
    default_agent_backend : str
        既定で利用する Agent backend の識別子。
    discord_bot_token : str | None
        Discord Bot へ接続するためのトークン。
    discord_application_id : str | None
        Discord アプリケーションの識別子。
    discord_trigger_mode : str
        Discord メッセージへ反応する条件。`mention` または `all`。
    codex_config : CodexAgentConfig
        Codex backend 用の設定。
    log_level : str
        ログ出力レベル。
    """

    chat_backend: str
    default_agent_backend: str
    discord_bot_token: str | None
    discord_application_id: str | None
    discord_trigger_mode: str
    codex_config: CodexAgentConfig
    log_level: str

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "AppConfig":
        """環境変数から設定を読み込む。

        Parameters
        ----------
        base_dir : Path | None, default=None
            相対パスを解決する基準ディレクトリ。未指定時は現在の作業ディレクトリを使う。

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
        default_agent_backend = _read_optional_env("AGENT_PORT_DEFAULT_AGENT")
        if default_agent_backend is None:
            default_agent_backend = os.getenv("AGENT_PORT_AGENT_BACKEND", "codex").strip()

        discord_bot_token = _read_optional_env("AGENT_PORT_DISCORD_BOT_TOKEN")
        discord_application_id = _read_optional_env("AGENT_PORT_DISCORD_APPLICATION_ID")
        discord_trigger_mode = _read_choice_env(
            name="AGENT_PORT_DISCORD_TRIGGER_MODE",
            default="mention",
            allowed_values={"mention", "all"},
        )

        codex_workspace_value = _read_optional_env("AGENT_PORT_CODEX_WORKSPACE")
        if codex_workspace_value is None:
            codex_workspace_value = os.getenv("AGENT_PORT_AGENT_WORKSPACE", ".")

        codex_command = os.getenv("AGENT_PORT_CODEX_COMMAND", "codex").strip()
        codex_timeout_seconds = _read_positive_int_env(
            name="AGENT_PORT_CODEX_TIMEOUT_SECONDS",
            default=300,
        )
        log_level = os.getenv("AGENT_PORT_LOG_LEVEL", "INFO")

        codex_config = CodexAgentConfig(
            backend_name="codex",
            workspace=_resolve_workspace_path(
                workspace_value=codex_workspace_value,
                base_dir=resolved_base_dir,
            ),
            command=codex_command,
            timeout_seconds=codex_timeout_seconds,
        )

        if chat_backend == "discord" and not discord_bot_token:
            raise ConfigError(
                "AGENT_PORT_CHAT_BACKEND=discord の場合は "
                "AGENT_PORT_DISCORD_BOT_TOKEN が必要です。"
            )
        if not codex_command:
            raise ConfigError("AGENT_PORT_CODEX_COMMAND は空文字にできません。")
        if default_agent_backend not in cls._build_agent_config_map(codex_config):
            raise ConfigError(
                "現在設定済みの Agent backend は codex のみです。"
            )

        return cls(
            chat_backend=chat_backend,
            default_agent_backend=default_agent_backend,
            discord_bot_token=discord_bot_token,
            discord_application_id=discord_application_id,
            discord_trigger_mode=discord_trigger_mode,
            codex_config=codex_config,
            log_level=log_level,
        )

    @staticmethod
    def _build_agent_config_map(
        codex_config: CodexAgentConfig,
    ) -> dict[str, AgentBackendConfig]:
        """backend 名から backend 設定を引ける辞書を構築する。

        Parameters
        ----------
        codex_config : CodexAgentConfig
            Codex backend 用の設定。

        Returns
        -------
        dict[str, AgentBackendConfig]
            backend 名をキーとした設定辞書。
        """

        return {"codex": codex_config}

    def get_agent_config(self, backend_name: str) -> AgentBackendConfig:
        """指定 backend の設定を返す。

        Parameters
        ----------
        backend_name : str
            取得対象の backend 名。

        Returns
        -------
        AgentBackendConfig
            backend に対応する設定。

        Raises
        ------
        ConfigError
            対応する backend 設定が存在しない場合。
        """

        agent_configs = self.list_agent_configs()
        if backend_name not in agent_configs:
            raise ConfigError(
                f"未対応の Agent backend が指定されました: {backend_name}"
            )
        return agent_configs[backend_name]

    def list_agent_configs(self) -> dict[str, AgentBackendConfig]:
        """利用可能な backend 設定一覧を返す。

        Returns
        -------
        dict[str, AgentBackendConfig]
            backend 名をキーとした設定辞書。
        """

        return self._build_agent_config_map(self.codex_config)

    def list_agent_backends(self) -> tuple[str, ...]:
        """利用可能な backend 名一覧を返す。

        Returns
        -------
        tuple[str, ...]
            利用可能な backend 名のタプル。
        """

        return tuple(self.list_agent_configs().keys())

    @property
    def agent_backend(self) -> str:
        """後方互換のために既定 backend 名を返す。"""

        return self.default_agent_backend

    @property
    def agent_workspace(self) -> Path:
        """後方互換のために既定 backend の workspace を返す。"""

        return self.get_agent_config(self.default_agent_backend).workspace

    @property
    def codex_command(self) -> str:
        """後方互換のために Codex CLI コマンド名を返す。"""

        return self.codex_config.command

    @property
    def codex_timeout_seconds(self) -> int:
        """後方互換のために Codex タイムアウト秒数を返す。"""

        return self.codex_config.timeout_seconds


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


def _read_choice_env(name: str, default: str, allowed_values: set[str]) -> str:
    """候補値のいずれかとして環境変数を読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : str
        値が未指定だった場合の既定値。
    allowed_values : set[str]
        許可する値の集合。

    Returns
    -------
    str
        許可された候補値のいずれか。

    Raises
    ------
    ConfigError
        許可されていない値が指定された場合。
    """

    raw_value = os.getenv(name, default).strip()
    if raw_value not in allowed_values:
        allowed_values_text = ", ".join(sorted(allowed_values))
        raise ConfigError(
            f"{name} は {allowed_values_text} のいずれかで指定してください。"
        )

    return raw_value


def _resolve_workspace_path(workspace_value: str, base_dir: Path) -> Path:
    """workspace のパスを絶対パスへ解決する。

    Parameters
    ----------
    workspace_value : str
        環境変数で受け取った workspace のパス文字列。
    base_dir : Path
        相対パスを解決する基準ディレクトリ。

    Returns
    -------
    Path
        解決済みの絶対パス。

    Raises
    ------
    ConfigError
        workspace が空文字だった場合や、存在しない場合。
    """

    normalized_value = workspace_value.strip()
    if not normalized_value:
        raise ConfigError("AGENT_PORT_CODEX_WORKSPACE は空文字にできません。")

    workspace_path = Path(normalized_value)
    if workspace_path.is_absolute():
        resolved_workspace = workspace_path.resolve()
    else:
        resolved_workspace = (base_dir / workspace_path).resolve()

    if not resolved_workspace.exists():
        raise ConfigError(
            "AGENT_PORT_CODEX_WORKSPACE が存在しません: "
            f"{resolved_workspace}"
        )
    if not resolved_workspace.is_dir():
        raise ConfigError(
            "AGENT_PORT_CODEX_WORKSPACE はディレクトリを指定してください: "
            f"{resolved_workspace}"
        )

    return resolved_workspace
