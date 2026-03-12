"""config モジュールの振る舞いを検証するテスト。"""

from pathlib import Path

import pytest

from agent_port.config import AppConfig, ConfigError


def test_from_env_reads_discord_and_workspace_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """環境変数から Discord 設定と workspace を読み込めることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        テスト用の環境変数を操作するためのフィクスチャ。
    tmp_path : Path
        一時ディレクトリを提供するフィクスチャ。

    Returns
    -------
    None
        読み込んだ設定値が期待どおりであることを検証する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.setenv("AGENT_PORT_AGENT_BACKEND", "codex")
    monkeypatch.setenv("AGENT_PORT_DISCORD_BOT_TOKEN", "discord-token")
    monkeypatch.setenv("AGENT_PORT_DISCORD_APPLICATION_ID", "123456")
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "all")
    monkeypatch.setenv("AGENT_PORT_AGENT_WORKSPACE", "workspace/project")
    monkeypatch.setenv("AGENT_PORT_CODEX_COMMAND", "codex")
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("AGENT_PORT_LOG_LEVEL", "DEBUG")

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat_backend == "discord"
    assert config.agent_backend == "codex"
    assert config.discord_bot_token == "discord-token"
    assert config.discord_application_id == "123456"
    assert config.discord_trigger_mode == "all"
    assert config.agent_workspace == (tmp_path / "workspace/project").resolve()
    assert config.codex_command == "codex"
    assert config.codex_timeout_seconds == 45
    assert config.log_level == "DEBUG"


def test_from_env_uses_defaults_when_optional_values_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """任意設定が未指定でも既定値で設定を組み立てられることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        テスト用の環境変数を操作するためのフィクスチャ。
    tmp_path : Path
        一時ディレクトリを提供するフィクスチャ。

    Returns
    -------
    None
        既定値が適用されることを検証する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat_backend == "console"
    assert config.agent_backend == "codex"
    assert config.discord_bot_token is None
    assert config.discord_application_id is None
    assert config.discord_trigger_mode == "mention"
    assert config.agent_workspace == tmp_path.resolve()
    assert config.codex_command == "codex"
    assert config.codex_timeout_seconds == 300
    assert config.log_level == "INFO"


def test_from_env_requires_discord_token_for_discord_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Discord バックエンドでは Bot トークンが必須であることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        テスト用の環境変数を操作するためのフィクスチャ。
    tmp_path : Path
        一時ディレクトリを提供するフィクスチャ。

    Returns
    -------
    None
        必須設定が不足した場合に例外が送出されることを検証する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.delenv("AGENT_PORT_DISCORD_BOT_TOKEN", raising=False)

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_absolute_workspace_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """workspace が絶対パスの場合は拒否することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        テスト用の環境変数を操作するためのフィクスチャ。
    tmp_path : Path
        一時ディレクトリを提供するフィクスチャ。

    Returns
    -------
    None
        相対パスのみ許可されることを検証する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_AGENT_WORKSPACE", str(tmp_path.resolve()))

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_non_positive_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Codex タイムアウトが 1 未満なら拒否することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        テスト用の環境変数を操作するためのフィクスチャ。
    tmp_path : Path
        一時ディレクトリを提供するフィクスチャ。

    Returns
    -------
    None
        不正なタイムアウト値で例外が送出されることを検証する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "0")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_unknown_trigger_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Discord の反応条件が未対応値なら拒否することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        テスト用の環境変数を操作するためのフィクスチャ。
    tmp_path : Path
        一時ディレクトリを提供するフィクスチャ。

    Returns
    -------
    None
        未対応の反応条件で例外が送出されることを検証する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "prefix")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)
