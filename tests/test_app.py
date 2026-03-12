"""app モジュールの起動要約を検証するテスト。"""

from pathlib import Path

from agent_port.app import build_startup_summary
from agent_port.config import AppConfig, CodexAgentConfig


def test_build_startup_summary_includes_selected_settings() -> None:
    """起動要約に主要設定が含まれることを検証する。

    Returns
    -------
    None
        既定 Agent と利用可能 backend 一覧が要約へ含まれることを確認する。
    """

    config = AppConfig(
        chat_backend="discord",
        default_agent_backend="codex",
        discord_bot_token="token",
        discord_application_id="app-id",
        discord_trigger_mode="mention",
        codex_config=CodexAgentConfig(
            backend_name="codex",
            workspace=Path("workspace").resolve(),
            command="codex",
            timeout_seconds=300,
        ),
        log_level="INFO",
    )

    summary = build_startup_summary(config)

    assert "chat_backend=discord" in summary
    assert "default_agent_backend=codex" in summary
    assert "available_agent_backends=codex" in summary
    assert "discord_trigger_mode=mention" in summary
    assert "codex_command=codex" in summary
