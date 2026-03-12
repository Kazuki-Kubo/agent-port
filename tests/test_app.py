"""app モジュールの起動要約を検証するテスト。"""

from pathlib import Path

from agent_port.app import build_startup_summary
from agent_port.config import AppConfig, CodexAgentConfig
from agent_port.workspaces import ManagedWorkspace, WorkspaceRegistry


def test_build_startup_summary_includes_selected_settings() -> None:
    """起動要約に主要設定が含まれることを検証する。

    Returns
    -------
    None
        既定 workspace と registry 情報が要約へ含まれることを確認する。
    """

    workspace_registry = WorkspaceRegistry(
        [
            ManagedWorkspace(
                workspace_id="sample",
                path=Path("..").resolve(),
                allowed_agents=("codex",),
            )
        ]
    )
    config = AppConfig(
        base_dir=Path(".").resolve(),
        chat_backend="discord",
        default_agent_backend="codex",
        default_workspace_id="sample",
        workspace_registry_path=Path("config/workspaces.json").resolve(),
        workspace_registry=workspace_registry,
        discord_bot_token="token",
        discord_application_id="app-id",
        discord_trigger_mode="mention",
        codex_config=CodexAgentConfig(
            backend_name="codex",
            command="codex",
            timeout_seconds=300,
        ),
        log_level="INFO",
    )

    summary = build_startup_summary(config)

    assert "chat_backend=discord" in summary
    assert "default_agent_backend=codex" in summary
    assert "default_workspace_id=sample" in summary
    assert "available_agent_backends=codex" in summary
    assert "available_workspace_ids=sample" in summary
    assert "codex_command=codex" in summary
