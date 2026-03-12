"""config モジュールの環境変数読み込みを検証するテスト。"""

from pathlib import Path

import pytest

from agent_port.config import AppConfig, ConfigError


def test_from_env_reads_discord_and_workspace_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Discord 設定と Codex 設定を環境変数から読めることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        読み込んだ設定が `AppConfig` へ正しく反映されることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_AGENT", "codex")
    monkeypatch.setenv("AGENT_PORT_DISCORD_BOT_TOKEN", "discord-token")
    monkeypatch.setenv("AGENT_PORT_DISCORD_APPLICATION_ID", "123456")
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "all")
    monkeypatch.setenv("AGENT_PORT_CODEX_WORKSPACE", "workspace/project")
    monkeypatch.setenv("AGENT_PORT_CODEX_COMMAND", "codex")
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("AGENT_PORT_LOG_LEVEL", "DEBUG")
    (tmp_path / "workspace/project").mkdir(parents=True)

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat_backend == "discord"
    assert config.default_agent_backend == "codex"
    assert config.agent_backend == "codex"
    assert config.discord_bot_token == "discord-token"
    assert config.discord_application_id == "123456"
    assert config.discord_trigger_mode == "all"
    assert config.codex_config.workspace == (tmp_path / "workspace/project").resolve()
    assert config.agent_workspace == (tmp_path / "workspace/project").resolve()
    assert config.codex_command == "codex"
    assert config.codex_timeout_seconds == 45
    assert config.log_level == "DEBUG"
    assert config.list_agent_backends() == ("codex",)


def test_from_env_uses_defaults_when_optional_values_are_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """任意設定がない場合でも既定値で構成できることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        console backend では Discord token なしで構成できることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat_backend == "console"
    assert config.default_agent_backend == "codex"
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
    """Discord backend では Bot token が必須であることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        token 未設定時に `ConfigError` になることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.delenv("AGENT_PORT_DISCORD_BOT_TOKEN", raising=False)

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_accepts_absolute_workspace_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Codex workspace に絶対パスを使えることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        絶対パスがそのまま採用されることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_CODEX_WORKSPACE", str(tmp_path.resolve()))

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.agent_workspace == tmp_path.resolve()


def test_from_env_rejects_missing_workspace_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """存在しない workspace を拒否することを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        不正パスで `ConfigError` になることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_CODEX_WORKSPACE", "missing-workspace")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_non_positive_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Codex timeout が 1 未満なら拒否することを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        不正値で `ConfigError` になることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "0")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_unknown_trigger_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """未対応の Discord trigger mode を拒否することを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        不正値で `ConfigError` になることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "prefix")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_uses_legacy_agent_backend_when_default_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """後方互換の `AGENT_PORT_AGENT_BACKEND` を読めることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。

    Returns
    -------
    None
        旧環境変数からも既定 Agent が設定されることを確認する。
    """

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_AGENT_BACKEND", "codex")

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.default_agent_backend == "codex"
