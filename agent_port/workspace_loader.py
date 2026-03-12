"""workspace registry の読込手順をまとめる。"""

from __future__ import annotations

from pathlib import Path

from agent_port.workspaces import (
    WorkspaceError,
    Workspaces,
    load_legacy_workspaces,
    load_workspaces_json,
)


def load_workspaces(
    base_dir: Path,
    workspace_file: str | None,
    default_workspace: str | None,
    legacy_workspace: str | None,
    error_factory: type[Exception],
) -> tuple[Workspaces, Path | None]:
    """workspace registry を読む。

    Parameters
    ----------
    base_dir : Path
        `agent-port` 本体ディレクトリ。
    workspace_file : str | None
        明示指定された registry ファイル。
    default_workspace : str | None
        既定 workspace ID。
    legacy_workspace : str | None
        旧環境変数の workspace パス。
    error_factory : type[Exception]
        変換時に使う例外型。

    Returns
    -------
    tuple[Workspaces, Path | None]
        読み込んだ registry と使用したファイルパス。
    """

    file_path: Path | None = None
    store = Workspaces([])

    if workspace_file is not None:
        file_path = _resolve_file(base_dir=base_dir, value=workspace_file)
        store = _load_file(file_path=file_path, control_root=base_dir, error_factory=error_factory)
    else:
        default_file = (base_dir / "config" / "workspaces.json").resolve()
        if default_file.exists():
            file_path = default_file
            store = _load_file(
                file_path=default_file,
                control_root=base_dir,
                error_factory=error_factory,
            )

    if store.is_empty() and legacy_workspace is not None:
        try:
            store = load_legacy_workspaces(
                workspace_id=default_workspace or "legacy",
                workspace_value=legacy_workspace,
                base_dir=base_dir,
                control_root=base_dir,
            )
        except WorkspaceError as exc:
            raise error_factory(str(exc)) from exc
        return store, None

    if store.is_empty():
        raise error_factory(
            "workspace registry が空です。"
            " `config/workspaces.json` を用意するか、旧設定の"
            " `AGENT_PORT_CODEX_WORKSPACE` を指定してください。"
        )

    return store, file_path


def resolve_default_workspace(
    workspaces: Workspaces,
    requested_workspace: str | None,
    legacy_workspace: str | None,
    error_factory: type[Exception],
) -> str:
    """既定 workspace ID を決める。

    Parameters
    ----------
    workspaces : Workspaces
        読み込み済み registry。
    requested_workspace : str | None
        明示指定の workspace ID。
    legacy_workspace : str | None
        旧環境変数の workspace パス。
    error_factory : type[Exception]
        検証失敗時に使う例外型。

    Returns
    -------
    str
        使用する workspace ID。
    """

    if requested_workspace is not None:
        return requested_workspace

    ids = workspaces.ids()
    if len(ids) == 1:
        return ids[0]
    if legacy_workspace is not None and "legacy" in ids:
        return "legacy"

    raise error_factory(
        "workspace が複数あるため AGENT_PORT_DEFAULT_WORKSPACE を指定してください。"
    )


def _resolve_file(base_dir: Path, value: str) -> Path:
    """registry ファイルの絶対パスを解決する。

    Parameters
    ----------
    base_dir : Path
        相対パス解決の基準。
    value : str
        ファイルパス文字列。

    Returns
    -------
    Path
        解決済みの絶対パス。
    """

    raw = Path(value)
    return raw.resolve() if raw.is_absolute() else (base_dir / raw).resolve()


def _load_file(
    file_path: Path,
    control_root: Path,
    error_factory: type[Exception],
) -> Workspaces:
    """registry ファイルを読む。

    Parameters
    ----------
    file_path : Path
        読み込む JSON ファイル。
    control_root : Path
        `agent-port` 本体ディレクトリ。
    error_factory : type[Exception]
        変換時に使う例外型。

    Returns
    -------
    Workspaces
        読み込んだ registry。
    """

    try:
        return load_workspaces_json(registry_path=file_path, control_root=control_root)
    except WorkspaceError as exc:
        raise error_factory(str(exc)) from exc


load_workspace_registry_from_sources = load_workspaces
resolve_default_workspace_id = resolve_default_workspace
