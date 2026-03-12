"""`.env` 読み込み処理を検証するテスト。"""

from pathlib import Path

from agent_port.config import AppConfig


def test_from_env_reads_values_from_dotenv_file(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """`.env` に書かれた値を環境変数として利用できることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        テスト用の環境変数を操作するためのフィクスチャ。
    tmp_path : Path
        一時ディレクトリを提供するフィクスチャ。

    Returns
    -------
    None
        `.env` の値から設定が組み立てられることを検証する。
    """

    dotenv_path = tmp_path / ".env"
    dotenv_path.write_text(
        "\n".join(
            [
                "AGENT_PORT_CHAT_BACKEND=discord",
                "AGENT_PORT_AGENT_BACKEND=codex",
                "AGENT_PORT_DISCORD_BOT_TOKEN=dotenv-token",
                "AGENT_PORT_AGENT_WORKSPACE=workspace/from-dotenv",
            ]
        ),
        encoding="utf-8",
    )
    (tmp_path / "workspace/from-dotenv").mkdir(parents=True)
    monkeypatch.delenv("AGENT_PORT_CHAT_BACKEND", raising=False)
    monkeypatch.delenv("AGENT_PORT_AGENT_BACKEND", raising=False)
    monkeypatch.delenv("AGENT_PORT_DISCORD_BOT_TOKEN", raising=False)
    monkeypatch.delenv("AGENT_PORT_AGENT_WORKSPACE", raising=False)

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat_backend == "discord"
    assert config.agent_backend == "codex"
    assert config.discord_bot_token == "dotenv-token"
    assert config.agent_workspace == (tmp_path / "workspace/from-dotenv").resolve()
