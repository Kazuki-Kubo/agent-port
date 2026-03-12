"""環境変数からアプリケーション設定を読み込むモジュール。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os

from agent_port.workspace_registry import (
    WorkspaceRegistry,
    WorkspaceRegistryError,
    create_legacy_workspace_registry,
    load_workspace_registry_from_json,
)


class ConfigError(ValueError):
    """設定値が不正な場合に送出する例外。"""


@dataclass(frozen=True)
class AgentBackendConfig:
    """Agent backend 共通設定を表す。

    Attributes
    ----------
    backend_name : str
        backend の識別名。
    """

    backend_name: str


@dataclass(frozen=True)
class CodexAgentConfig(AgentBackendConfig):
    """Codex backend の設定を表す。

    Attributes
    ----------
    backend_name : str
        backend の識別名。通常は `codex`。
    command : str
        実行する Codex CLI コマンド。
    timeout_seconds : int
        Codex 実行タイムアウト秒数。
    """

    command: str
    timeout_seconds: int


@dataclass(frozen=True)
class AppConfig:
    """アプリケーション全体の設定を表す。

    Attributes
    ----------
    base_dir : Path
        `agent-port` 本体ディレクトリ。
    chat_backend : str
        利用するチャット backend。
    default_agent_backend : str
        既定の agent backend 名。
    default_workspace_id : str
        既定の workspace ID。
    workspace_registry_path : Path | None
        workspace registry JSON のパス。legacy 指定のみの場合は `None`。
    workspace_registry : WorkspaceRegistry
        管理対象 workspace の registry。
    discord_bot_token : str | None
        Discord Bot token。
    discord_application_id : str | None
        Discord application ID。
    discord_trigger_mode : str
        `mention` または `all`。
    codex_config : CodexAgentConfig
        Codex backend 用設定。
    log_level : str
        ログレベル。
    """

    base_dir: Path
    chat_backend: str
    default_agent_backend: str
    default_workspace_id: str
    workspace_registry_path: Path | None
    workspace_registry: WorkspaceRegistry
    discord_bot_token: str | None
    discord_application_id: str | None
    discord_trigger_mode: str
    codex_config: CodexAgentConfig
    log_level: str

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "AppConfig":
        """環境変数から設定を構築する。

        Parameters
        ----------
        base_dir : Path | None, default=None
            本体ディレクトリ。未指定時はカレントディレクトリ。

        Returns
        -------
        AppConfig
            読み込んだ設定を反映したオブジェクト。

        Raises
        ------
        ConfigError
            必須設定不足や workspace 設定不正の場合。
        """

        resolved_base_dir = (base_dir or Path.cwd()).resolve()
        load_dotenv_file(base_dir=resolved_base_dir)

        chat_backend = os.getenv("AGENT_PORT_CHAT_BACKEND", "discord").strip()
        default_agent_backend = _read_optional_env("AGENT_PORT_DEFAULT_AGENT")
        if default_agent_backend is None:
            default_agent_backend = os.getenv("AGENT_PORT_AGENT_BACKEND", "codex").strip()

        default_workspace_id = _read_optional_env("AGENT_PORT_DEFAULT_WORKSPACE")
        workspace_registry_path = _read_optional_env("AGENT_PORT_WORKSPACE_REGISTRY")
        discord_bot_token = _read_optional_env("AGENT_PORT_DISCORD_BOT_TOKEN")
        discord_application_id = _read_optional_env("AGENT_PORT_DISCORD_APPLICATION_ID")
        discord_trigger_mode = _read_choice_env(
            name="AGENT_PORT_DISCORD_TRIGGER_MODE",
            default="mention",
            allowed_values={"mention", "all"},
        )

        legacy_workspace_value = _read_optional_env("AGENT_PORT_CODEX_WORKSPACE")
        if legacy_workspace_value is None:
            legacy_workspace_value = _read_optional_env("AGENT_PORT_AGENT_WORKSPACE")

        codex_command = os.getenv("AGENT_PORT_CODEX_COMMAND", "codex").strip()
        codex_timeout_seconds = _read_positive_int_env(
            name="AGENT_PORT_CODEX_TIMEOUT_SECONDS",
            default=300,
        )
        log_level = os.getenv("AGENT_PORT_LOG_LEVEL", "INFO").strip()

        if not codex_command:
            raise ConfigError("AGENT_PORT_CODEX_COMMAND は空文字にできません。")

        codex_config = CodexAgentConfig(
            backend_name="codex",
            command=codex_command,
            timeout_seconds=codex_timeout_seconds,
        )

        workspace_registry, resolved_registry_path = _load_workspace_registry(
            base_dir=resolved_base_dir,
            workspace_registry_path=workspace_registry_path,
            default_workspace_id=default_workspace_id,
            legacy_workspace_value=legacy_workspace_value,
        )
        resolved_default_workspace_id = _resolve_default_workspace_id(
            workspace_registry=workspace_registry,
            requested_workspace_id=default_workspace_id,
            legacy_workspace_value=legacy_workspace_value,
        )

        if chat_backend == "discord" and not discord_bot_token:
            raise ConfigError(
                "AGENT_PORT_CHAT_BACKEND=discord の場合は "
                "AGENT_PORT_DISCORD_BOT_TOKEN が必須です。"
            )
        if default_agent_backend not in cls._build_agent_config_map(codex_config):
            raise ConfigError(
                "現在利用可能な Agent backend は codex のみです。"
            )

        try:
            workspace_registry.get_workspace(resolved_default_workspace_id)
        except WorkspaceRegistryError as exc:
            raise ConfigError(str(exc)) from exc

        return cls(
            base_dir=resolved_base_dir,
            chat_backend=chat_backend,
            default_agent_backend=default_agent_backend,
            default_workspace_id=resolved_default_workspace_id,
            workspace_registry_path=resolved_registry_path,
            workspace_registry=workspace_registry,
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
        """backend 名ごとの設定マップを返す。

        Parameters
        ----------
        codex_config : CodexAgentConfig
            Codex backend 用設定。

        Returns
        -------
        dict[str, AgentBackendConfig]
            backend 名をキーにした設定マップ。
        """

        return {"codex": codex_config}

    def get_agent_config(self, backend_name: str) -> AgentBackendConfig:
        """指定 backend の設定を返す。

        Parameters
        ----------
        backend_name : str
            参照対象の backend 名。

        Returns
        -------
        AgentBackendConfig
            backend に対応する設定。
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
            backend 名ごとの設定マップ。
        """

        return self._build_agent_config_map(self.codex_config)

    def list_agent_backends(self) -> tuple[str, ...]:
        """利用可能な backend 名一覧を返す。

        Returns
        -------
        tuple[str, ...]
            backend 名一覧。
        """

        return tuple(self.list_agent_configs().keys())

    def list_workspace_ids(self) -> tuple[str, ...]:
        """利用可能な workspace ID 一覧を返す。

        Returns
        -------
        tuple[str, ...]
            registry に登録された workspace ID 一覧。
        """

        return self.workspace_registry.list_workspace_ids()

    def get_workspace_path(self, workspace_id: str) -> Path:
        """workspace_id から path を解決する。

        Parameters
        ----------
        workspace_id : str
            解決対象の workspace ID。

        Returns
        -------
        Path
            workspace ディレクトリの絶対パス。
        """

        try:
            return self.workspace_registry.get_workspace(workspace_id).path
        except WorkspaceRegistryError as exc:
            raise ConfigError(str(exc)) from exc

    @property
    def agent_backend(self) -> str:
        """後方互換用に既定 backend 名を返す。"""

        return self.default_agent_backend

    @property
    def agent_workspace(self) -> Path:
        """後方互換用に既定 workspace の path を返す。"""

        return self.get_workspace_path(self.default_workspace_id)

    @property
    def codex_command(self) -> str:
        """後方互換用に Codex コマンド名を返す。"""

        return self.codex_config.command

    @property
    def codex_timeout_seconds(self) -> int:
        """後方互換用に Codex timeout を返す。"""

        return self.codex_config.timeout_seconds


def load_dotenv_file(base_dir: Path) -> None:
    """`.env` を読み込む。

    Parameters
    ----------
    base_dir : Path
        `.env` を探す基準ディレクトリ。

    Returns
    -------
    None
        未設定の環境変数だけを `.env` から補う。
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


def _load_workspace_registry(
    base_dir: Path,
    workspace_registry_path: str | None,
    default_workspace_id: str | None,
    legacy_workspace_value: str | None,
) -> tuple[WorkspaceRegistry, Path | None]:
    """workspace registry を読み込む。

    Parameters
    ----------
    base_dir : Path
        `agent-port` 本体ディレクトリ。
    workspace_registry_path : str | None
        registry JSON のパス文字列。
    default_workspace_id : str | None
        既定 workspace ID。
    legacy_workspace_value : str | None
        旧環境変数による直接 workspace path。

    Returns
    -------
    tuple[WorkspaceRegistry, Path | None]
        読み込んだ registry と、使った registry ファイルパス。
    """

    resolved_registry_path: Path | None = None
    registry = WorkspaceRegistry([])

    if workspace_registry_path is not None:
        raw_registry_path = Path(workspace_registry_path)
        resolved_registry_path = (
            raw_registry_path.resolve()
            if raw_registry_path.is_absolute()
            else (base_dir / raw_registry_path).resolve()
        )
        try:
            registry = load_workspace_registry_from_json(
                registry_path=resolved_registry_path,
                control_root=base_dir,
            )
        except WorkspaceRegistryError as exc:
            raise ConfigError(str(exc)) from exc
    else:
        default_registry_path = (base_dir / "config/workspaces.json").resolve()
        if default_registry_path.exists():
            resolved_registry_path = default_registry_path
            try:
                registry = load_workspace_registry_from_json(
                    registry_path=default_registry_path,
                    control_root=base_dir,
                )
            except WorkspaceRegistryError as exc:
                raise ConfigError(str(exc)) from exc

    if registry.is_empty() and legacy_workspace_value is not None:
        legacy_workspace_id = default_workspace_id or "legacy"
        try:
            registry = create_legacy_workspace_registry(
                workspace_id=legacy_workspace_id,
                workspace_value=legacy_workspace_value,
                base_dir=base_dir,
                control_root=base_dir,
            )
        except WorkspaceRegistryError as exc:
            raise ConfigError(str(exc)) from exc
        return registry, None

    if registry.is_empty():
        raise ConfigError(
            "workspace registry が空です。config/workspaces.json を作成するか、"
            "後方互換の AGENT_PORT_CODEX_WORKSPACE を設定してください。"
        )

    return registry, resolved_registry_path


def _resolve_default_workspace_id(
    workspace_registry: WorkspaceRegistry,
    requested_workspace_id: str | None,
    legacy_workspace_value: str | None,
) -> str:
    """既定 workspace ID を確定する。

    Parameters
    ----------
    workspace_registry : WorkspaceRegistry
        読み込み済み registry。
    requested_workspace_id : str | None
        明示指定された既定 workspace ID。
    legacy_workspace_value : str | None
        旧環境変数による直接 path 指定。

    Returns
    -------
    str
        実際に採用する既定 workspace ID。
    """

    if requested_workspace_id is not None:
        return requested_workspace_id

    workspace_ids = workspace_registry.list_workspace_ids()
    if len(workspace_ids) == 1:
        return workspace_ids[0]

    if legacy_workspace_value is not None and "legacy" in workspace_ids:
        return "legacy"

    raise ConfigError(
        "workspace が複数あるため AGENT_PORT_DEFAULT_WORKSPACE を指定してください。"
    )


def _read_optional_env(name: str) -> str | None:
    """環境変数を空白除去して読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。

    Returns
    -------
    str | None
        値があれば空白除去後の文字列、空なら `None`。
    """

    value = os.getenv(name)
    if value is None:
        return None
    stripped_value = value.strip()
    return stripped_value or None


def _read_positive_int_env(name: str, default: int) -> int:
    """正の整数環境変数を読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : int
        未設定時の既定値。

    Returns
    -------
    int
        読み込んだ整数値。
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
    """候補内の値だけ許可する環境変数を読み込む。

    Parameters
    ----------
    name : str
        読み込む環境変数名。
    default : str
        未設定時の既定値。
    allowed_values : set[str]
        許可する値一覧。

    Returns
    -------
    str
        許可された値。
    """

    raw_value = os.getenv(name, default).strip()
    if raw_value not in allowed_values:
        allowed_values_text = ", ".join(sorted(allowed_values))
        raise ConfigError(
            f"{name} は {allowed_values_text} のいずれかで指定してください。"
        )

    return raw_value
