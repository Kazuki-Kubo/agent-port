"""config モジュールの環境変数読み込みを検証するテスト。"""

from pathlib import Path

import pytest

from agent_port.config import AppConfig, ConfigError


def test_from_env_reads_discord_and_workspace_registry_settings(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Discord 設定と workspace registry 設定を読めることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替えるための fixture。
    tmp_path : Path
        テスト用一時ディレクトリ。

    Returns
    -------
    None
        registry 経由の設定が `AppConfig` に反映されることを確認する。
    """

    workspace_root = tmp_path.parent / "external-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_id="project",
        workspace_path=workspace_root,
    )

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_AGENT", "codex")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )
    monkeypatch.setenv("AGENT_PORT_DISCORD_BOT_TOKEN", "discord-token")
    monkeypatch.setenv("AGENT_PORT_DISCORD_APPLICATION_ID", "123456")
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "all")
    monkeypatch.setenv("AGENT_PORT_CODEX_COMMAND", "codex")
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("AGENT_PORT_LOG_LEVEL", "DEBUG")

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat_backend == "discord"
    assert config.default_agent_backend == "codex"
    assert config.default_workspace_id == "project"
    assert config.discord_bot_token == "discord-token"
    assert config.discord_application_id == "123456"
    assert config.discord_trigger_mode == "all"
    assert config.workspace_registry_path == registry_path.resolve()
    assert config.agent_workspace == workspace_root.resolve()
    assert config.codex_command == "codex"
    assert config.codex_timeout_seconds == 45
    assert config.log_level == "DEBUG"
    assert config.list_agent_backends() == ("codex",)
    assert config.list_workspace_ids() == ("project",)


def test_from_env_auto_selects_only_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """workspace が 1 件なら既定 ID 未指定でも自動選択されることを検証する。"""

    workspace_root = tmp_path.parent / "single-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_id="single",
        workspace_path=workspace_root,
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.default_workspace_id == "single"
    assert config.agent_workspace == workspace_root.resolve()


def test_from_env_requires_discord_token_for_discord_backend(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Discord backend では Bot token が必須であることを検証する。"""

    workspace_root = tmp_path.parent / "discord-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_id="project",
        workspace_path=workspace_root,
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )
    monkeypatch.delenv("AGENT_PORT_DISCORD_BOT_TOKEN", raising=False)

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_accepts_absolute_workspace_path_in_registry(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """registry 内では絶対パスの workspace も使えることを検証する。"""

    workspace_root = tmp_path.parent / "absolute-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_id="project",
        workspace_path=workspace_root.resolve(),
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.agent_workspace == workspace_root.resolve()


def test_from_env_rejects_missing_workspace_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """存在しない workspace を registry で指定した場合に拒否することを検証する。"""

    registry_dir = tmp_path / "config"
    registry_dir.mkdir()
    registry_path = registry_dir / "workspaces.json"
    registry_path.write_text(
        '{"workspaces":[{"id":"project","path":"../missing"}]}',
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_workspace_inside_control_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """本体ディレクトリ配下の workspace を拒否することを検証する。"""

    internal_workspace = tmp_path / "workspace"
    internal_workspace.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_id="internal",
        workspace_path=internal_workspace,
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "internal")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_non_positive_timeout(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Codex timeout が 1 未満なら拒否することを検証する。"""

    workspace_root = tmp_path.parent / "timeout-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_id="project",
        workspace_path=workspace_root,
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "0")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_unknown_trigger_mode(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """未対応の Discord trigger mode を拒否することを検証する。"""

    workspace_root = tmp_path.parent / "trigger-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_id="project",
        workspace_path=workspace_root,
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "prefix")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_uses_legacy_workspace_env_when_registry_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """registry 未設定時に旧 workspace 環境変数から移行できることを検証する。"""

    workspace_root = tmp_path.parent / "legacy-workspace"
    workspace_root.mkdir()
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_CODEX_WORKSPACE", str(workspace_root))

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.default_workspace_id == "legacy"
    assert config.agent_workspace == workspace_root.resolve()
    assert config.workspace_registry_path is None


def test_from_env_requires_default_workspace_when_registry_has_multiple_entries(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """workspace が複数ある場合は既定 ID 指定が必要であることを検証する。"""

    first_workspace = tmp_path.parent / "first-workspace"
    second_workspace = tmp_path.parent / "second-workspace"
    first_workspace.mkdir()
    second_workspace.mkdir()
    registry_dir = tmp_path / "config"
    registry_dir.mkdir()
    registry_path = registry_dir / "workspaces.json"
    registry_path.write_text(
        (
            '{"workspaces":['
            f'{{"id":"first","path":"{first_workspace.as_posix()}"}},'
            f'{{"id":"second","path":"{second_workspace.as_posix()}"}}'
            "]} "
        ).strip(),
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def _write_workspace_registry(
    base_dir: Path,
    workspace_id: str,
    workspace_path: Path,
) -> Path:
    """テスト用 workspace registry JSON を書き出す。

    Parameters
    ----------
    base_dir : Path
        registry ファイルを置く基準ディレクトリ。
    workspace_id : str
        書き込む workspace ID。
    workspace_path : Path
        書き込む workspace path。

    Returns
    -------
    Path
        作成した registry ファイルパス。
    """

    registry_dir = base_dir / "config"
    registry_dir.mkdir()
    registry_path = registry_dir / "workspaces.json"
    registry_path.write_text(
        (
            '{"workspaces":['
            f'{{"id":"{workspace_id}","path":"{workspace_path.as_posix()}","allowed_agents":["codex"]}}'
            "]}"
        ),
        encoding="utf-8",
    )
    return registry_path
