"""`.env` 読み込みを確認する。"""

from pathlib import Path

import pytest

from agent_port.config import AppConfig


def test_from_env_reads_values_from_dotenv_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """`.env` から設定を補完できることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数削除用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        `.env` の値が `AppConfig` に反映されることを確認する。
    """

    workspace_root = tmp_path.parent / "dotenv-workspace"
    workspace_root.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    registry_path = config_dir / "workspaces.json"
    registry_path.write_text(
        (
            '{"workspaces":['
            f'{{"id":"dotenv","path":"{workspace_root.as_posix()}","allowed_agents":["codex"]}}'
            "]} "
        ).strip(),
        encoding="utf-8",
    )
    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "AGENT_PORT_CHAT_BACKEND=discord",
                "AGENT_PORT_DEFAULT_AGENT=codex",
                "AGENT_PORT_DEFAULT_WORKSPACE=dotenv",
                "AGENT_PORT_WORKSPACE_REGISTRY=config/workspaces.json",
                "AGENT_PORT_DISCORD_BOT_TOKEN=dotenv-token",
            ]
        ),
        encoding="utf-8",
    )

    for name in (
        "AGENT_PORT_CHAT_BACKEND",
        "AGENT_PORT_DEFAULT_AGENT",
        "AGENT_PORT_DEFAULT_WORKSPACE",
        "AGENT_PORT_WORKSPACE_REGISTRY",
        "AGENT_PORT_DISCORD_BOT_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat == "discord"
    assert config.default_agent == "codex"
    assert config.discord_token == "dotenv-token"
    assert config.default_workspace == "dotenv"
    assert config.workspace == workspace_root.resolve()
