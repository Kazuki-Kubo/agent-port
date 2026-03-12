"""外部 workspace の定義と読み込みを扱う。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


class WorkspaceError(ValueError):
    """workspace 定義の検証失敗を表す。"""


@dataclass(frozen=True)
class Workspace:
    """workspace 1 件分の情報を表す。

    Attributes
    ----------
    workspace_id : str
        workspace を識別する ID。
    path : Path
        解決済みの実パス。
    allowed_agents : tuple[str, ...]
        利用を許可する agent 名。
    description : str | None, default=None
        補足説明。
    """

    workspace_id: str
    path: Path
    allowed_agents: tuple[str, ...]
    description: str | None = None

    def supports(self, backend_name: str) -> bool:
        """backend を利用できるか返す。

        Parameters
        ----------
        backend_name : str
            判定する backend 名。

        Returns
        -------
        bool
            `allowed_agents` が空、または backend 名を含むなら `True`。
        """

        return not self.allowed_agents or backend_name in self.allowed_agents

    def supports_agent(self, backend_name: str) -> bool:
        """旧名の互換メソッド。

        Parameters
        ----------
        backend_name : str
            判定する backend 名。

        Returns
        -------
        bool
            `supports()` の結果。
        """

        return self.supports(backend_name)


class Workspaces:
    """workspace の registry を表す。"""

    def __init__(self, items: list[Workspace]) -> None:
        """registry を初期化する。

        Parameters
        ----------
        items : list[Workspace]
            登録する workspace 一覧。
        """

        self._items: dict[str, Workspace] = {}
        for item in items:
            if item.workspace_id in self._items:
                raise WorkspaceError(f"workspace_id が重複しています: {item.workspace_id}")
            self._items[item.workspace_id] = item

    def get(self, workspace_id: str) -> Workspace:
        """workspace を取得する。

        Parameters
        ----------
        workspace_id : str
            取得する workspace ID。

        Returns
        -------
        Workspace
            対応する workspace。
        """

        if workspace_id not in self._items:
            raise WorkspaceError(f"workspace_id が見つかりません: {workspace_id}")
        return self._items[workspace_id]

    def ids(self) -> tuple[str, ...]:
        """登録済み ID 一覧を返す。

        Returns
        -------
        tuple[str, ...]
            workspace ID 一覧。
        """

        return tuple(self._items.keys())

    def list(self) -> tuple[Workspace, ...]:
        """workspace 一覧を返す。

        Returns
        -------
        tuple[Workspace, ...]
            登録済み workspace 一覧。
        """

        return tuple(self._items.values())

    def is_empty(self) -> bool:
        """空かどうか返す。

        Returns
        -------
        bool
            1 件もなければ `True`。
        """

        return not self._items

    def get_workspace(self, workspace_id: str) -> Workspace:
        """旧名の互換メソッド。

        Parameters
        ----------
        workspace_id : str
            取得する workspace ID。

        Returns
        -------
        Workspace
            `get()` の結果。
        """

        return self.get(workspace_id)

    def list_workspace_ids(self) -> tuple[str, ...]:
        """旧名の互換メソッド。

        Returns
        -------
        tuple[str, ...]
            `ids()` の結果。
        """

        return self.ids()

    def list_workspaces(self) -> tuple[Workspace, ...]:
        """旧名の互換メソッド。

        Returns
        -------
        tuple[Workspace, ...]
            `list()` の結果。
        """

        return self.list()


def load_workspaces_json(registry_path: Path, control_root: Path) -> Workspaces:
    """JSON から workspace registry を読む。

    Parameters
    ----------
    registry_path : Path
        registry JSON のパス。
    control_root : Path
        `agent-port` 本体ディレクトリ。

    Returns
    -------
    Workspaces
        読み込んだ registry。
    """

    if not registry_path.exists():
        return Workspaces([])

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkspaceError(
            f"workspace registry JSON を読み込めません: {registry_path}"
        ) from exc

    raw_items = payload.get("workspaces", [])
    if not isinstance(raw_items, list):
        raise WorkspaceError("workspace registry の `workspaces` は配列で指定してください。")

    base_dir = registry_path.parent
    items = [
        _parse_workspace(item, registry_base=base_dir, control_root=control_root)
        for item in raw_items
    ]
    return Workspaces(items)


def load_legacy_workspaces(
    workspace_id: str,
    workspace_value: str,
    base_dir: Path,
    control_root: Path,
) -> Workspaces:
    """旧環境変数から 1 件だけ workspace を作る。

    Parameters
    ----------
    workspace_id : str
        作成する workspace ID。
    workspace_value : str
        環境変数に入っているパス文字列。
    base_dir : Path
        相対パス解決の基準。
    control_root : Path
        `agent-port` 本体ディレクトリ。

    Returns
    -------
    Workspaces
        1 件だけ含む registry。
    """

    return Workspaces(
        [
            Workspace(
                workspace_id=workspace_id,
                path=resolve_workspace_dir(
                    workspace_value=workspace_value,
                    base_dir=base_dir,
                    control_root=control_root,
                ),
                allowed_agents=(),
                description="legacy environment workspace",
            )
        ]
    )


def resolve_workspace_dir(
    workspace_value: str,
    base_dir: Path,
    control_root: Path,
) -> Path:
    """workspace パスを解決して検証する。

    Parameters
    ----------
    workspace_value : str
        指定されたパス文字列。
    base_dir : Path
        相対パス解決の基準。
    control_root : Path
        `agent-port` 本体ディレクトリ。

    Returns
    -------
    Path
        検証済みの絶対パス。
    """

    value = workspace_value.strip()
    if not value:
        raise WorkspaceError("workspace path は空にできません。")

    raw_path = Path(value)
    path = raw_path.resolve() if raw_path.is_absolute() else (base_dir / raw_path).resolve()
    control_root = control_root.resolve()

    if not path.exists():
        raise WorkspaceError(f"workspace が存在しません: {path}")
    if not path.is_dir():
        raise WorkspaceError(f"workspace はディレクトリで指定してください: {path}")
    if path == control_root or control_root in path.parents:
        raise WorkspaceError(
            "workspace に agent-port 本体ディレクトリまたはその配下は指定できません: "
            f"{path}"
        )

    return path


def _parse_workspace(
    raw_item: object,
    registry_base: Path,
    control_root: Path,
) -> Workspace:
    """JSON の 1 エントリを `Workspace` に変換する。

    Parameters
    ----------
    raw_item : object
        JSON の生データ。
    registry_base : Path
        registry ファイルの親ディレクトリ。
    control_root : Path
        `agent-port` 本体ディレクトリ。

    Returns
    -------
    Workspace
        変換後の workspace。
    """

    if not isinstance(raw_item, dict):
        raise WorkspaceError("workspace 定義はオブジェクトで指定してください。")

    workspace_id = str(raw_item.get("id", "")).strip()
    workspace_path = str(raw_item.get("path", "")).strip()
    if not workspace_id:
        raise WorkspaceError("workspace 定義には `id` が必要です。")
    if not workspace_path:
        raise WorkspaceError(f"workspace path が空です: {workspace_id}")

    raw_agents = raw_item.get("allowed_agents", [])
    if not isinstance(raw_agents, list):
        raise WorkspaceError(f"`allowed_agents` は配列で指定してください: {workspace_id}")

    allowed_agents = tuple(
        str(agent).strip() for agent in raw_agents if str(agent).strip()
    )
    description = raw_item.get("description")
    normalized_description = str(description).strip() if description is not None else None

    return Workspace(
        workspace_id=workspace_id,
        path=resolve_workspace_dir(
            workspace_value=workspace_path,
            base_dir=registry_base,
            control_root=control_root,
        ),
        allowed_agents=allowed_agents,
        description=normalized_description or None,
    )


ManagedWorkspace = Workspace
WorkspaceRegistry = Workspaces
WorkspaceRegistryError = WorkspaceError
load_workspace_registry_from_json = load_workspaces_json
create_legacy_workspace_registry = load_legacy_workspaces
resolve_workspace_path = resolve_workspace_dir
