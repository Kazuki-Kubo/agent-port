"""CLI の挙動を確認する。"""

from pathlib import Path

import pytest

from agent_port import cli


def test_main_runs_gateway_without_args(monkeypatch: pytest.MonkeyPatch) -> None:
    """引数なしで gateway が起動されることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        関数差し替え用 fixture。

    Returns
    -------
    None
        `run_gateway()` が呼ばれることを確認する。
    """

    monkeypatch.setattr(cli, "run_gateway", lambda: 7)

    assert cli.main([]) == 7


def test_config_validate_ok(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """`config validate` が正常終了することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力取得用 fixture。

    Returns
    -------
    None
        `valid` と表示されることを確認する。
    """

    workspace_root = tmp_path.parent / "cli-valid-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, workspace_root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))
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
    """`workspace list` で一覧が表示されることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力取得用 fixture。

    Returns
    -------
    None
        workspace ID と path が出力されることを確認する。
    """

    workspace_root = tmp_path.parent / "cli-list-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, workspace_root)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))
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
    """legacy 設定時は `(legacy env)` が出ることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力取得用 fixture。

    Returns
    -------
    None
        registry ファイルではなく legacy 表示になることを確認する。
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
    """`setup` が雛形ファイルを作ることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        作業ディレクトリ変更用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力取得用 fixture。

    Returns
    -------
    None
        `.env` と `config/workspaces.json` が作られることを確認する。
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
    """`setup --force` でも `.env` は保護されることを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        作業ディレクトリ変更用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力取得用 fixture。

    Returns
    -------
    None
        `.env` は保持され、workspace 定義は上書きされることを確認する。
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
    """`doctor` が正常状態を表示することを確認する。

    Parameters
    ----------
    monkeypatch : pytest.MonkeyPatch
        環境差し替え用 fixture。
    tmp_path : Path
        テスト用ディレクトリ。
    capsys : pytest.CaptureFixture[str]
        標準出力取得用 fixture。

    Returns
    -------
    None
        `ok` と既定 workspace が出力されることを確認する。
    """

    workspace_root = tmp_path.parent / "cli-doctor-workspace"
    workspace_root.mkdir()
    registry_path = _write_workspaces(tmp_path, workspace_root)
    (tmp_path / ".env").write_text("AGENT_PORT_CHAT_BACKEND=console\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("AGENT_PORT_CHAT_BACKEND", "console")
    monkeypatch.setenv("AGENT_PORT_WORKSPACE_REGISTRY", str(registry_path.relative_to(tmp_path)))
    monkeypatch.setenv("AGENT_PORT_DEFAULT_WORKSPACE", "sample")
    monkeypatch.setenv("AGENT_PORT_CODEX_COMMAND", "codex")
    codex_exe = workspace_root / "codex.exe"
    codex_exe.write_text("", encoding="utf-8")
    monkeypatch.setattr(
        cli.shutil,
        "which",
        lambda command: str(codex_exe) if command == "codex" else None,
    )

    exit_code = cli.main(["doctor"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "ok" in captured.out
    assert "default_workspace=sample" in captured.out


def _write_workspaces(base_dir: Path, workspace_path: Path) -> Path:
    """workspace registry を作る。

    Parameters
    ----------
    base_dir : Path
        registry を置くディレクトリ。
    workspace_path : Path
        登録する workspace の実パス。

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
            f'{{"id":"sample","path":"{workspace_path.as_posix()}","allowed_agents":["codex"]}}'
            "]} "
        ).strip(),
        encoding="utf-8",
    )
    return registry_path
