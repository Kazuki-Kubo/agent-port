"""app モジュールの要約表示を確認する。"""

from pathlib import Path

from agent_port.app import build_startup_summary
from agent_port.config import AppConfig, CodexConfig
from agent_port.workspaces import Workspace, Workspaces


def test_build_startup_summary_shows_main_settings() -> None:
    """起動サマリーに主要設定が含まれることを確認する。

    Returns
    -------
    None
        短いキー名で主要設定が表示されることを確認する。
    """

    config = AppConfig(
        base_dir=Path(".").resolve(),
        chat="discord",
        default_agent="codex",
        default_workspace="sample",
        workspace_file=Path("config/workspaces.json").resolve(),
        workspaces=Workspaces(
            [
                Workspace(
                    workspace_id="sample",
                    path=Path("..").resolve(),
                    allowed_agents=("codex",),
                )
            ]
        ),
        discord_token="token",
        discord_app_id="app-id",
        discord_trigger="mention",
        codex=CodexConfig(name="codex", command="codex", timeout=300),
        log_level="INFO",
    )

    summary = build_startup_summary(config)

    assert "chat=discord" in summary
    assert "default_agent=codex" in summary
    assert "default_workspace=sample" in summary
    assert "agents=codex" in summary
    assert "workspaces=sample" in summary
    assert "codex_command=codex" in summary
