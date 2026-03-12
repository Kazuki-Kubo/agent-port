"""CLI の挙動を検証するテスト。"""

from pathlib import Path

import pytest

from agent_port import cli


def test_main_runs_gateway_without_args(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """引数なし実行が gateway 起動へ委譲されることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        CLI 呼び出し先を差し替える fixture。

    Returns
    -------
    None
        `run_gateway_command` の戻り値がそのまま返ることを確認する。
    """

    monkeypatch.setattr(cli, "run_gateway_command", lambda: 7)

    assert cli.main([]) == 7


def test_config_validate_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`config validate` が有効設定で成功することを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替える fixture。
    tmp_path : Path
        テスト用一時ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力を検査する fixture。

    Returns
    -------
    None
        終了コード 0 と `valid` 出力を確認する。
    """

    workspace_root = tmp_path.parent / "cli-valid-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_path=workspace_root,
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "sample")

    exit_code = cli.main(["config", "validate"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "valid" in captured.out


def test_workspace_list_shows_workspace(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`workspace list` が登録済み workspace を表示することを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替える fixture。
    tmp_path : Path
        テスト用一時ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力を検査する fixture。

    Returns
    -------
    None
        一覧出力に workspace ID と path が含まれることを確認する。
    """

    workspace_root = tmp_path.parent / "cli-list-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_path=workspace_root,
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "sample")

    exit_code = cli.main(["workspace", "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "sample" in captured.out
    assert str(workspace_root.resolve()) in captured.out


def test_config_file_shows_legacy_env(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """legacy workspace 指定では `config file` が legacy 表示になることを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数を差し替える fixture。
    tmp_path : Path
        テスト用一時ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力を検査する fixture。

    Returns
    -------
    None
        `legacy env` 表示を確認する。
    """

    workspace_root = tmp_path.parent / "cli-legacy-workspace"
    workspace_root.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_CODEX_WORKSPACE", str(workspace_root))

    exit_code = cli.main(["config", "file"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "(legacy env)" in captured.out


def test_setup_creates_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`setup` が雛形ファイルを配置することを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        作業ディレクトリを差し替える fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力を取得する fixture。

    Returns
    -------
    None
        `.env` と `config/workspaces.json` が作成されることを確認する。
    """

    (tmp_path / ".env.example").write_text("AGENT_PORT_CHAT_BACKEND=discord\n", encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "workspaces.json.example").write_text('{"workspaces":[]}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["setup"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert (tmp_path / ".env").exists()
    assert (config_dir / "workspaces.json").exists()
    assert "created .env" in captured.out


def test_setup_force_keeps_existing_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`setup --force` でも既存 `.env` を上書きしないことを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        作業ディレクトリを差し替える fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力を取得する fixture。

    Returns
    -------
    None
        `.env` の内容が保持され、保護メッセージが出ることを確認する。
    """

    env_path = tmp_path / ".env"
    env_path.write_text("SECRET_TOKEN=keep-me\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("SECRET_TOKEN=replace-me\n", encoding="utf-8")
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "workspaces.json").write_text('{"workspaces":[{"id":"before"}]}', encoding="utf-8")
    (config_dir / "workspaces.json.example").write_text('{"workspaces":[]}', encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    exit_code = cli.main(["setup", "--force"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert env_path.read_text(encoding="utf-8") == "SECRET_TOKEN=keep-me\n"
    assert "protected .env" in captured.out
    assert (config_dir / "workspaces.json").read_text(encoding="utf-8") == '{"workspaces":[]}'


def test_doctor_reports_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`doctor` が正常な設定を `ok` と診断することを検証する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境変数と作業ディレクトリを差し替える fixture。
    tmp_path : Path
        テスト用の一時ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力を取得する fixture。

    Returns
    -------
    None
        正常終了し、`ok` と既定 workspace ID が出力されることを確認する。
    """

    workspace_root = tmp_path.parent / "cli-doctor-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspace_registry(
        base_dir=tmp_path,
        workspace_path=workspace_root,
    )
    (tmp_path / ".env").write_text("AGENT_PORT_CHAT_BACKEND=console\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv(
        "AGENT_PORT_WORKSPACE_REGISTRY",
        str(registry_path.relative_to(tmp_path)),
    )
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "sample")
    monkeypatch.setenv("AGENT_PORT_CODEX_COMMAND", "codex")
    codex_executable = workspace_root / "codex.exe"
    codex_executable.write_text("", encoding="utf-8")
    monkeypatch.setattr(cli.shutil, "which", lambda command: str(codex_executable) if command == "codex" else None)

    exit_code = cli.main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ok" in captured.out
    assert "default_workspace_id=sample" in captured.out


def _write_workspace_registry(base_dir: Path, workspace_path: Path) -> Path:
    """CLI テスト用 workspace registry を作成する。

    Parameters
    ----------
    base_dir : Path
        registry を置く基準ディレクトリ。
    workspace_path : Path
        登録する workspace path。

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
            f'{{"id":"sample","path":"{workspace_path.as_posix()}","allowed_agents":["codex"]}}'
            "]} "
        ).strip(),
        encoding="utf-8",
    )
    return registry_path
