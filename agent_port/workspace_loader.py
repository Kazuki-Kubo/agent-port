"""workspace registry の設定読み込みを補助するモジュール。"""

from __future__ import annotations

from pathlib import Path

from agent_port.workspaces import (
    WorkspaceRegistry,
    WorkspaceRegistryError,
    create_legacy_workspace_registry,
    load_workspace_registry_from_json,
)


def load_workspace_registry_from_sources(
    base_dir: Path,
    workspace_registry_path: str | None,
    default_workspace_id: str | None,
    legacy_workspace_value: str | None,
    error_factory: type[Exception],
) -> tuple[WorkspaceRegistry, Path | None]:
    """workspace registry を読み込む。

    Parameters
    ----------
    base_dir : Path
        `agent-port` 本体ディレクトリ。
    workspace_registry_path : str | None
        registry JSON のパス文字列。
    default_workspace_id : str | None
        既定 workspace ID。
    legacy_workspace_value : str | None
        旧環境変数による直接 workspace path。
    error_factory : type[Exception]
        エラー時に送出する例外型。

    Returns
    -------
    tuple[WorkspaceRegistry, Path | None]
        読み込んだ registry と、使った registry ファイルパス。
    """

    resolved_registry_path: Path | None = None
    registry = WorkspaceRegistry([])

    if workspace_registry_path is not None:
        raw_registry_path = Path(workspace_registry_path)
        resolved_registry_path = (
            raw_registry_path.resolve()
            if raw_registry_path.is_absolute()
            else (base_dir / raw_registry_path).resolve()
        )
        registry = _load_registry_file(
            registry_path=resolved_registry_path,
            control_root=base_dir,
            error_factory=error_factory,
        )
    else:
        default_registry_path = (base_dir / "config/workspaces.json").resolve()
        if default_registry_path.exists():
            resolved_registry_path = default_registry_path
            registry = _load_registry_file(
                registry_path=default_registry_path,
                control_root=base_dir,
                error_factory=error_factory,
            )

    if registry.is_empty() and legacy_workspace_value is not None:
        legacy_workspace_id = default_workspace_id or "legacy"
        try:
            registry = create_legacy_workspace_registry(
                workspace_id=legacy_workspace_id,
                workspace_value=legacy_workspace_value,
                base_dir=base_dir,
                control_root=base_dir,
            )
        except WorkspaceRegistryError as exc:
            raise error_factory(str(exc)) from exc
        return registry, None

    if registry.is_empty():
        raise error_factory(
            "workspace registry が空です。config/workspaces.json を作成するか、"
            "後方互換の AGENT_PORT_CODEX_WORKSPACE を設定してください。"
        )

    return registry, resolved_registry_path


def resolve_default_workspace_id(
    workspace_registry: WorkspaceRegistry,
    requested_workspace_id: str | None,
    legacy_workspace_value: str | None,
    error_factory: type[Exception],
) -> str:
    """既定 workspace ID を確定する。

    Parameters
    ----------
    workspace_registry : WorkspaceRegistry
        読み込み済み registry。
    requested_workspace_id : str | None
        明示指定された既定 workspace ID。
    legacy_workspace_value : str | None
        旧環境変数による直接 path 指定。
    error_factory : type[Exception]
        エラー時に送出する例外型。

    Returns
    -------
    str
        実際に採用する既定 workspace ID。
    """

    if requested_workspace_id is not None:
        return requested_workspace_id

    workspace_ids = workspace_registry.list_workspace_ids()
    if len(workspace_ids) == 1:
        return workspace_ids[0]

    if legacy_workspace_value is not None and "legacy" in workspace_ids:
        return "legacy"

    raise error_factory(
        "workspace が複数あるため AGENT_PORT_DEFAULT_WORKSPACE を指定してください。"
    )


def _load_registry_file(
    registry_path: Path,
    control_root: Path,
    error_factory: type[Exception],
) -> WorkspaceRegistry:
    """workspace registry JSON ファイルを読み込む。

    Parameters
    ----------
    registry_path : Path
        読み込む registry ファイルパス。
    control_root : Path
        `agent-port` 本体ディレクトリ。
    error_factory : type[Exception]
        エラー時に送出する例外型。

    Returns
    -------
    WorkspaceRegistry
        読み込んだ registry。
    """

    try:
        return load_workspace_registry_from_json(
            registry_path=registry_path,
            control_root=control_root,
        )
    except WorkspaceRegistryError as exc:
        raise error_factory(str(exc)) from exc
