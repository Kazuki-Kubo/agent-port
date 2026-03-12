"""環境変数からアプリ設定を組み立てる。"""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path

from agent_port.env import (
    load_dotenv_file,
    read_choice_env,
    read_optional_env,
    read_positive_int_env,
)
from agent_port.workspace_loader import load_workspaces, resolve_default_workspace
from agent_port.workspaces import WorkspaceError, Workspaces


class ConfigError(ValueError):
    """設定値の検証失敗を表す。"""


@dataclass(frozen=True)
class BackendConfig:
    """backend 共通設定を表す。

    Attributes
    ----------
    name : str
        backend 名。
    """

    name: str


@dataclass(frozen=True)
class CodexConfig(BackendConfig):
    """Codex backend の設定を表す。

    Attributes
    ----------
    name : str
        backend 名。
    command : str
        Codex CLI コマンド。
    timeout : int
        タイムアウト秒数。
    """

    command: str
    timeout: int


@dataclass(frozen=True)
class AppConfig:
    """アプリ全体の設定を表す。

    Attributes
    ----------
    base_dir : Path
        `agent-port` 本体ディレクトリ。
    chat : str
        chat backend 名。
    default_agent : str
        既定 agent 名。
    default_workspace : str
        既定 workspace ID。
    workspace_file : Path | None
        使用した workspace registry ファイル。
    workspaces : Workspaces
        読み込み済み workspace registry。
    discord_token : str | None
        Discord Bot token。
    discord_app_id : str | None
        Discord application ID。
    discord_trigger : str
        Discord の反応条件。`mention` または `all`。
    codex : CodexConfig
        Codex 設定。
    log_level : str
        ログレベル。
    """

    base_dir: Path
    chat: str
    default_agent: str
    default_workspace: str
    workspace_file: Path | None
    workspaces: Workspaces
    discord_token: str | None
    discord_app_id: str | None
    discord_trigger: str
    codex: CodexConfig
    log_level: str

    @classmethod
    def from_env(cls, base_dir: Path | None = None) -> "AppConfig":
        """環境変数から設定を読む。

        Parameters
        ----------
        base_dir : Path | None, default=None
            基準ディレクトリ。`None` のときはカレントディレクトリ。

        Returns
        -------
        AppConfig
            構築済み設定。
        """

        base = (base_dir or Path.cwd()).resolve()
        load_dotenv_file(base)

        chat = os.getenv("AGENT_PORT_CHAT_BACKEND", "discord").strip()
        default_agent = read_optional_env("AGENT_PORT_DEFAULT_AGENT")
        if default_agent is None:
            default_agent = os.getenv("AGENT_PORT_AGENT_BACKEND", "codex").strip()

        requested_workspace = read_optional_env("AGENT_PORT_DEFAULT_WORKSPACE")
        workspace_file = read_optional_env("AGENT_PORT_WORKSPACE_REGISTRY")
        discord_token = read_optional_env("AGENT_PORT_DISCORD_BOT_TOKEN")
        discord_app_id = read_optional_env("AGENT_PORT_DISCORD_APPLICATION_ID")
        discord_trigger = read_choice_env(
            name="AGENT_PORT_DISCORD_TRIGGER_MODE",
            default="mention",
            allowed_values={"mention", "all"},
            error_factory=ConfigError,
        )

        legacy_workspace = read_optional_env("AGENT_PORT_CODEX_WORKSPACE")
        if legacy_workspace is None:
            legacy_workspace = read_optional_env("AGENT_PORT_AGENT_WORKSPACE")

        codex_command = os.getenv("AGENT_PORT_CODEX_COMMAND", "codex").strip()
        if not codex_command:
            raise ConfigError("AGENT_PORT_CODEX_COMMAND は空にできません。")

        codex_timeout = read_positive_int_env(
            name="AGENT_PORT_CODEX_TIMEOUT_SECONDS",
            default=300,
            error_factory=ConfigError,
        )
        log_level = os.getenv("AGENT_PORT_LOG_LEVEL", "INFO").strip() or "INFO"

        codex = CodexConfig(name="codex", command=codex_command, timeout=codex_timeout)
        workspaces, resolved_file = load_workspaces(
            base_dir=base,
            workspace_file=workspace_file,
            default_workspace=requested_workspace,
            legacy_workspace=legacy_workspace,
            error_factory=ConfigError,
        )
        default_workspace = resolve_default_workspace(
            workspaces=workspaces,
            requested_workspace=requested_workspace,
            legacy_workspace=legacy_workspace,
            error_factory=ConfigError,
        )

        if chat == "discord" and not discord_token:
            raise ConfigError(
                "AGENT_PORT_CHAT_BACKEND=discord のときは "
                "AGENT_PORT_DISCORD_BOT_TOKEN が必要です。"
            )

        backends = cls._backend_map(codex)
        if default_agent not in backends:
            raise ConfigError("現在利用できる Agent backend は codex のみです。")

        try:
            workspaces.get(default_workspace)
        except WorkspaceError as exc:
            raise ConfigError(str(exc)) from exc

        return cls(
            base_dir=base,
            chat=chat,
            default_agent=default_agent,
            default_workspace=default_workspace,
            workspace_file=resolved_file,
            workspaces=workspaces,
            discord_token=discord_token,
            discord_app_id=discord_app_id,
            discord_trigger=discord_trigger,
            codex=codex,
            log_level=log_level,
        )

    @staticmethod
    def _backend_map(codex: CodexConfig) -> dict[str, BackendConfig]:
        """利用可能 backend 一覧を返す。

        Parameters
        ----------
        codex : CodexConfig
            Codex 設定。

        Returns
        -------
        dict[str, BackendConfig]
            backend 名と設定の対応。
        """

        return {"codex": codex}

    def get_backend(self, name: str) -> BackendConfig:
        """backend 設定を返す。

        Parameters
        ----------
        name : str
            backend 名。

        Returns
        -------
        BackendConfig
            対応する設定。
        """

        backends = self.list_backends_config()
        if name not in backends:
            raise ConfigError(f"未対応の Agent backend です: {name}")
        return backends[name]

    def list_backends_config(self) -> dict[str, BackendConfig]:
        """backend 設定一覧を返す。

        Returns
        -------
        dict[str, BackendConfig]
            backend 設定一覧。
        """

        return self._backend_map(self.codex)

    def list_backends(self) -> tuple[str, ...]:
        """backend 名一覧を返す。

        Returns
        -------
        tuple[str, ...]
            backend 名一覧。
        """

        return tuple(self.list_backends_config().keys())

    def list_agent_backends(self) -> tuple[str, ...]:
        """旧名の互換メソッド。

        Returns
        -------
        tuple[str, ...]
            `list_backends()` の結果。
        """

        return self.list_backends()

    def list_workspace_ids(self) -> tuple[str, ...]:
        """workspace ID 一覧を返す。

        Returns
        -------
        tuple[str, ...]
            workspace ID 一覧。
        """

        return self.workspaces.ids()

    def get_workspace_dir(self, workspace_id: str) -> Path:
        """workspace の実パスを返す。

        Parameters
        ----------
        workspace_id : str
            workspace ID。

        Returns
        -------
        Path
            対応する実パス。
        """

        try:
            return self.workspaces.get(workspace_id).path
        except WorkspaceError as exc:
            raise ConfigError(str(exc)) from exc

    @property
    def backend(self) -> str:
        """既定 backend 名を返す。

        Returns
        -------
        str
            既定 backend 名。
        """

        return self.default_agent

    @property
    def workspace(self) -> Path:
        """既定 workspace の実パスを返す。

        Returns
        -------
        Path
            既定 workspace の実パス。
        """

        return self.get_workspace_dir(self.default_workspace)

    @property
    def codex_command(self) -> str:
        """Codex コマンドを返す。

        Returns
        -------
        str
            Codex コマンド。
        """

        return self.codex.command

    @property
    def codex_timeout(self) -> int:
        """Codex タイムアウト秒数を返す。

        Returns
        -------
        int
            タイムアウト秒数。
        """

        return self.codex.timeout

    @property
    def chat_backend(self) -> str:
        """旧名の互換プロパティ。

        Returns
        -------
        str
            `chat` の値。
        """

        return self.chat

    @property
    def default_agent_backend(self) -> str:
        """旧名の互換プロパティ。

        Returns
        -------
        str
            `default_agent` の値。
        """

        return self.default_agent

    @property
    def default_workspace_id(self) -> str:
        """旧名の互換プロパティ。

        Returns
        -------
        str
            `default_workspace` の値。
        """

        return self.default_workspace

    @property
    def workspace_registry_path(self) -> Path | None:
        """旧名の互換プロパティ。

        Returns
        -------
        Path | None
            `workspace_file` の値。
        """

        return self.workspace_file

    @property
    def workspace_registry(self) -> Workspaces:
        """旧名の互換プロパティ。

        Returns
        -------
        Workspaces
            `workspaces` の値。
        """

        return self.workspaces

    @property
    def discord_bot_token(self) -> str | None:
        """旧名の互換プロパティ。

        Returns
        -------
        str | None
            `discord_token` の値。
        """

        return self.discord_token

    @property
    def discord_application_id(self) -> str | None:
        """旧名の互換プロパティ。

        Returns
        -------
        str | None
            `discord_app_id` の値。
        """

        return self.discord_app_id

    @property
    def discord_trigger_mode(self) -> str:
        """旧名の互換プロパティ。

        Returns
        -------
        str
            `discord_trigger` の値。
        """

        return self.discord_trigger

    @property
    def codex_config(self) -> CodexConfig:
        """旧名の互換プロパティ。

        Returns
        -------
        CodexConfig
            `codex` の値。
        """

        return self.codex

    @property
    def agent_backend(self) -> str:
        """旧名の互換プロパティ。

        Returns
        -------
        str
            `default_agent` の値。
        """

        return self.default_agent

    @property
    def agent_workspace(self) -> Path:
        """旧名の互換プロパティ。

        Returns
        -------
        Path
            `workspace` の値。
        """

        return self.workspace

    @property
    def codex_timeout_seconds(self) -> int:
        """旧名の互換プロパティ。

        Returns
        -------
        int
            `codex_timeout` の値。
        """

        return self.codex_timeout


AgentBackendConfig = BackendConfig
CodexAgentConfig = CodexConfig
