"""config 読み込みを確認する。"""

from pathlib import Path

import pytest

from agent_port.config import AppConfig, ConfigError


def test_from_env_reads_discord_and_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Discord 設定と registry を読めることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        各設定値が `AppConfig` に反映されることを確認する。
    """

    workspace_root = tmp_path.parent / "external-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, "project", workspace_root)

    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_AGENT", "codex")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))
    monkeypatch.setenv("AGENT_PORT_DISCORD_BOT_TOKEN", "discord-token")
    monkeypatch.setenv("AGENT_PORT_DISCORD_APPLICATION_ID", "123456")
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "all")
    monkeypatch.setenv("AGENT_PORT_CODEX_COMMAND", "codex")
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("AGENT_PORT_LOG_LEVEL", "DEBUG")

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.chat == "discord"
    assert config.default_agent == "codex"
    assert config.default_workspace == "project"
    assert config.discord_token == "discord-token"
    assert config.discord_app_id == "123456"
    assert config.discord_trigger == "all"
    assert config.workspace_file == registry_path.resolve()
    assert config.workspace == workspace_root.resolve()
    assert config.codex_command == "codex"
    assert config.codex_timeout == 45
    assert config.log_level == "DEBUG"
    assert config.list_backends() == ("codex",)
    assert config.list_workspace_ids() == ("project",)


def test_from_env_auto_selects_only_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """workspace が 1 件なら既定値なしでも選ばれることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        1 件だけなら自動選択されることを確認する。
    """

    workspace_root = tmp_path.parent / "single-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, "single", workspace_root)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.default_workspace == "single"
    assert config.workspace == workspace_root.resolve()


def test_from_env_requires_discord_token(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Discord backend では token が必須であることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        token 未設定で例外になることを確認する。
    """

    workspace_root = tmp_path.parent / "discord-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, "project", workspace_root)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "discord")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))
    monkeypatch.delenv("AGENT_PORT_DISCORD_BOT_TOKEN", raising=False)

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_accepts_absolute_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """registry では絶対パス workspace も使えることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        絶対パスがそのまま解決されることを確認する。
    """

    workspace_root = tmp_path.parent / "absolute-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, "project", workspace_root.resolve())
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.workspace == workspace_root.resolve()


def test_from_env_rejects_missing_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """存在しない workspace を拒否することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        解決できない path で例外になることを確認する。
    """

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    registry_path = config_dir / "workspaces.json"
    registry_path.write_text(
        '{"workspaces":[{"id":"project","path":"../missing"}]}',
        encoding="utf-8",
    )
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_control_root_child(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """本体配下の workspace を拒否することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        control root 配下で例外になることを確認する。
    """

    internal_workspace = tmp_path / "workspace"
    internal_workspace.mkdir()
    registry_path = _write_workspaces(tmp_path, "internal", internal_workspace)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "internal")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_non_positive_timeout(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """0 以下の timeout を拒否することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        timeout が 0 だと例外になることを確認する。
    """

    workspace_root = tmp_path.parent / "timeout-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, "project", workspace_root)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))
    monkeypatch.setenv("AGENT_PORT_CODEX_TIMEOUT_SECONDS", "0")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_rejects_unknown_trigger(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """未対応の trigger mode を拒否することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        `mention` と `all` 以外で例外になることを確認する。
    """

    workspace_root = tmp_path.parent / "trigger-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, "project", workspace_root)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "project")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))
    monkeypatch.setenv("AGENT_PORT_DISCORD_TRIGGER_MODE", "prefix")

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def test_from_env_uses_legacy_workspace(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """registry がないときは legacy workspace を使うことを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        `legacy` workspace が生成されることを確認する。
    """

    workspace_root = tmp_path.parent / "legacy-workspace"
    workspace_root.mkdir()
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_CODEX_WORKSPACE", str(workspace_root))

    config = AppConfig.from_env(base_dir=tmp_path)

    assert config.default_workspace == "legacy"
    assert config.workspace == workspace_root.resolve()
    assert config.workspace_file is None


def test_from_env_requires_default_workspace_for_multiple_items(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """workspace が複数あると既定 ID が必須であることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。

    Returns
    -------
    None
        既定 workspace 未指定で例外になることを確認する。
    """

    first_workspace = tmp_path.parent / "first-workspace"
    second_workspace = tmp_path.parent / "second-workspace"
    first_workspace.mkdir()
    second_workspace.mkdir()
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    registry_path = config_dir / "workspaces.json"
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
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))

    with pytest.raises(ConfigError):
        AppConfig.from_env(base_dir=tmp_path)


def _write_workspaces(base_dir: Path, workspace_id: str, workspace_path: Path) -> Path:
    """workspace registry を作る。

    Parameters
    ----------
    base_dir : Path
        registry を置くディレクトリ。
    workspace_id : str
        登録する workspace ID。
    workspace_path : Path
        登録する workspace の path。

    Returns
    -------
    Path
        作成した registry ファイル。
    """

    config_dir = base_dir / "config"
    config_dir.mkdir()
    registry_path = config_dir / "workspaces.json"
    registry_path.write_text(
        (
            '{"workspaces":['
            f'{{"id":"{workspace_id}","path":"{workspace_path.as_posix()}","allowed_agents":["codex"]}}'
            "]} "
        ).strip(),
        encoding="utf-8",
    )
    return registry_path
