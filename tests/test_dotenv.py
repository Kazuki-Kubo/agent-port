"""`.env` 読み込み挙動を検証するテスト。"""

from pathlib import Path

from agent_port.config import AppConfig


def test_from_env_reads_values_from_dotenv_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """`.env` に書かれた設定を利用できることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数初期値を消すための fixture。
    tmp_path : Path
        テスト用一時ディレクトリ。

    Returns
    -------
    None
        `.env` の値から workspace registry と Discord token が読まれることを確認する。
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
            "]}"
        ),
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
    monkeypatch.delenv("AGENT_PORT_CHAT_BACKEND", raising=False)
    monkeypatch.delenv("AGENT_PORT_DEFAULT_AGENT", raising=False)
    monkeypatch.delenv("AGENT_PORT_DEFAULT_WORKSPACE", raising=False)
    monkeypatch.delenv("AGENT_PORT_WORKSPACE_REGISTRY", raising=False)
    monkeypatch.delenv("AGENT_PORT_DISCORD_BOT_TOKEN", raising=False)

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat_backend == "discord"
    assert config.agent_backend == "codex"
    assert config.discord_bot_token == "dotenv-token"
    assert config.default_workspace_id == "dotenv"
    assert config.agent_workspace == workspace_root.resolve()
