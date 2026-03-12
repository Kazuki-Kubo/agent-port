"""環境変数からアプリケーション設定を読み込むモジュール。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from agent_port.env_utils import (
    load_dotenv_file,
    read_choice_env,
    read_optional_env,
    read_positive_int_env,
)
from agent_port.workspace_config import (
    load_workspace_registry_from_sources,
    resolve_default_workspace_id,
)
from agent_port.workspace_registry import WorkspaceRegistry, WorkspaceRegistryError


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
        default_agent_backend = read_optional_env("AGENT_PORT_DEFAULT_AGENT")
        if default_agent_backend is None:
            default_agent_backend = os.getenv("AGENT_PORT_AGENT_BACKEND", "codex").strip()

        default_workspace_id = read_optional_env("AGENT_PORT_DEFAULT_WORKSPACE")
        workspace_registry_path = read_optional_env("AGENT_PORT_WORKSPACE_REGISTRY")
        discord_bot_token = read_optional_env("AGENT_PORT_DISCORD_BOT_TOKEN")
        discord_application_id = read_optional_env("AGENT_PORT_DISCORD_APPLICATION_ID")
        discord_trigger_mode = read_choice_env(
            name="AGENT_PORT_DISCORD_TRIGGER_MODE",
            default="mention",
            allowed_values={"mention", "all"},
            error_factory=ConfigError,
        )

        legacy_workspace_value = read_optional_env("AGENT_PORT_CODEX_WORKSPACE")
        if legacy_workspace_value is None:
            legacy_workspace_value = read_optional_env("AGENT_PORT_AGENT_WORKSPACE")

        codex_command = os.getenv("AGENT_PORT_CODEX_COMMAND", "codex").strip()
        codex_timeout_seconds = read_positive_int_env(
            name="AGENT_PORT_CODEX_TIMEOUT_SECONDS",
            default=300,
            error_factory=ConfigError,
        )
        log_level = os.getenv("AGENT_PORT_LOG_LEVEL", "INFO").strip()

        if not codex_command:
            raise ConfigError("AGENT_PORT_CODEX_COMMAND は空文字にできません。")

        codex_config = CodexAgentConfig(
            backend_name="codex",
            command=codex_command,
            timeout_seconds=codex_timeout_seconds,
        )

        workspace_registry, resolved_registry_path = load_workspace_registry_from_sources(
            base_dir=resolved_base_dir,
            workspace_registry_path=workspace_registry_path,
            default_workspace_id=default_workspace_id,
            legacy_workspace_value=legacy_workspace_value,
            error_factory=ConfigError,
        )
        resolved_default_workspace_id = resolve_default_workspace_id(
            workspace_registry=workspace_registry,
            requested_workspace_id=default_workspace_id,
            legacy_workspace_value=legacy_workspace_value,
            error_factory=ConfigError,
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
