"""app モジュールの振る舞いを検証するテスト。"""

from pathlib import Path

from agent_port.app import build_startup_summary
from agent_port.config import AppConfig


def test_build_startup_summary_includes_selected_settings() -> None:
    """起動サマリーに主要な設定値が含まれることを確認する。

    Returns
    -------
    None
        サマリー文字列に期待する設定行が含まれることを検証する。
    """

    config = AppConfig(
        chat_backend="discord",
        agent_backend="codex",
        discord_bot_token="token",
        discord_application_id="app-id",
        discord_trigger_mode="mention",
        agent_workspace=Path("workspace").resolve(),
        codex_command="codex",
        codex_timeout_seconds=300,
        log_level="INFO",
    )

    summary = build_startup_summary(config)

    assert "chat_backend=discord" in summary
    assert "agent_backend=codex" in summary
    assert "discord_trigger_mode=mention" in summary
    assert "codex_command=codex" in summary
