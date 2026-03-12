"""agent-port が管理する外部 workspace の registry。"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


class WorkspaceRegistryError(ValueError):
    """workspace registry の読み込みや参照に失敗した場合の例外。"""


@dataclass(frozen=True)
class ManagedWorkspace:
    """agent-port が管理する外部 workspace を表す。

    Attributes
    ----------
    workspace_id : str
        workspace を識別する短い ID。
    path : Path
        実際の workspace ディレクトリ。
    allowed_agents : tuple[str, ...]
        この workspace で利用を許可する agent backend 一覧。空なら全許可。
    description : str | None
        workspace の用途説明。
    """

    workspace_id: str
    path: Path
    allowed_agents: tuple[str, ...]
    description: str | None = None

    def supports_agent(self, backend_name: str) -> bool:
        """指定 backend を利用できるか判定する。

        Parameters
        ----------
        backend_name : str
            判定対象の agent backend 名。

        Returns
        -------
        bool
            `allowed_agents` が空、または backend 名を含む場合は `True`。
        """

        return not self.allowed_agents or backend_name in self.allowed_agents


class WorkspaceRegistry:
    """workspace_id から外部 workspace を引く registry。"""

    def __init__(self, workspaces: list[ManagedWorkspace]) -> None:
        """registry を初期化する。

        Parameters
        ----------
        workspaces : list[ManagedWorkspace]
            登録する workspace 一覧。

        Returns
        -------
        None
            workspace_id ごとの lookup table を構築する。
        """

        self._workspaces: dict[str, ManagedWorkspace] = {}
        for workspace in workspaces:
            if workspace.workspace_id in self._workspaces:
                raise WorkspaceRegistryError(
                    f"workspace_id が重複しています: {workspace.workspace_id}"
                )
            self._workspaces[workspace.workspace_id] = workspace

    def get_workspace(self, workspace_id: str) -> ManagedWorkspace:
        """workspace_id から workspace を取得する。

        Parameters
        ----------
        workspace_id : str
            取得対象の workspace ID。

        Returns
        -------
        ManagedWorkspace
            対応する workspace 定義。

        Raises
        ------
        WorkspaceRegistryError
            指定 ID が未登録の場合。
        """

        if workspace_id not in self._workspaces:
            raise WorkspaceRegistryError(
                f"workspace_id が登録されていません: {workspace_id}"
            )
        return self._workspaces[workspace_id]

    def list_workspace_ids(self) -> tuple[str, ...]:
        """登録済み workspace ID 一覧を返す。

        Returns
        -------
        tuple[str, ...]
            利用可能な workspace ID 一覧。
        """

        return tuple(self._workspaces.keys())

    def list_workspaces(self) -> tuple[ManagedWorkspace, ...]:
        """登録済み workspace 一覧を返す。

        Returns
        -------
        tuple[ManagedWorkspace, ...]
            登録順の workspace 一覧。
        """

        return tuple(self._workspaces.values())

    def is_empty(self) -> bool:
        """registry が空かどうかを返す。

        Returns
        -------
        bool
            1 件も登録がなければ `True`。
        """

        return not self._workspaces


def load_workspace_registry_from_json(
    registry_path: Path,
    control_root: Path,
) -> WorkspaceRegistry:
    """JSON ファイルから workspace registry を読み込む。

    Parameters
    ----------
    registry_path : Path
        registry JSON ファイルの絶対パス。
    control_root : Path
        `agent-port` 本体ディレクトリの絶対パス。

    Returns
    -------
    WorkspaceRegistry
        読み込んだ workspace registry。

    Raises
    ------
    WorkspaceRegistryError
        JSON 形式不正や不正 workspace パスが含まれる場合。
    """

    if not registry_path.exists():
        return WorkspaceRegistry([])

    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise WorkspaceRegistryError(
            f"workspace registry JSON を読み込めません: {registry_path}"
        ) from exc

    raw_workspaces = payload.get("workspaces", [])
    if not isinstance(raw_workspaces, list):
        raise WorkspaceRegistryError(
            "workspace registry の `workspaces` は配列で指定してください。"
        )

    registry_base_dir = registry_path.parent
    workspaces: list[ManagedWorkspace] = []
    for raw_workspace in raw_workspaces:
        workspaces.append(
            _parse_workspace_definition(
                raw_workspace=raw_workspace,
                registry_base_dir=registry_base_dir,
                control_root=control_root,
            )
        )

    return WorkspaceRegistry(workspaces)


def create_legacy_workspace_registry(
    workspace_id: str,
    workspace_value: str,
    base_dir: Path,
    control_root: Path,
) -> WorkspaceRegistry:
    """旧環境変数指定の単一 workspace から registry を作る。

    Parameters
    ----------
    workspace_id : str
        仮想的に割り当てる workspace ID。
    workspace_value : str
        環境変数に書かれた path 文字列。
    base_dir : Path
        相対パス解決に使う基準ディレクトリ。
    control_root : Path
        `agent-port` 本体ディレクトリ。

    Returns
    -------
    WorkspaceRegistry
        単一 workspace を持つ registry。
    """

    managed_workspace = ManagedWorkspace(
        workspace_id=workspace_id,
        path=resolve_workspace_path(
            workspace_value=workspace_value,
            base_dir=base_dir,
            control_root=control_root,
        ),
        allowed_agents=(),
        description="legacy environment workspace",
    )
    return WorkspaceRegistry([managed_workspace])


def resolve_workspace_path(
    workspace_value: str,
    base_dir: Path,
    control_root: Path,
) -> Path:
    """workspace path を解決して妥当性を確認する。

    Parameters
    ----------
    workspace_value : str
        registry または環境変数で指定された path 文字列。
    base_dir : Path
        相対パス解決に使う基準ディレクトリ。
    control_root : Path
        `agent-port` 本体ディレクトリ。

    Returns
    -------
    Path
        解決済みの絶対パス。

    Raises
    ------
    WorkspaceRegistryError
        path が空、不存在、ディレクトリでない、本体配下である場合。
    """

    normalized_value = workspace_value.strip()
    if not normalized_value:
        raise WorkspaceRegistryError("workspace path は空文字にできません。")

    workspace_path = Path(normalized_value)
    resolved_workspace = (
        workspace_path.resolve()
        if workspace_path.is_absolute()
        else (base_dir / workspace_path).resolve()
    )

    if not resolved_workspace.exists():
        raise WorkspaceRegistryError(
            f"workspace が存在しません: {resolved_workspace}"
        )
    if not resolved_workspace.is_dir():
        raise WorkspaceRegistryError(
            f"workspace はディレクトリを指定してください: {resolved_workspace}"
        )
    if resolved_workspace == control_root or control_root in resolved_workspace.parents:
        raise WorkspaceRegistryError(
            "workspace に agent-port 本体ディレクトリまたはその配下は指定できません: "
            f"{resolved_workspace}"
        )

    return resolved_workspace


def _parse_workspace_definition(
    raw_workspace: object,
    registry_base_dir: Path,
    control_root: Path,
) -> ManagedWorkspace:
    """1 件の workspace 定義を `ManagedWorkspace` へ変換する。

    Parameters
    ----------
    raw_workspace : object
        JSON から読み出した 1 件分の定義。
    registry_base_dir : Path
        registry ファイルの親ディレクトリ。
    control_root : Path
        `agent-port` 本体ディレクトリ。

    Returns
    -------
    ManagedWorkspace
        検証済み workspace 定義。
    """

    if not isinstance(raw_workspace, dict):
        raise WorkspaceRegistryError("workspace 定義はオブジェクトで指定してください。")

    workspace_id = str(raw_workspace.get("id", "")).strip()
    workspace_path = str(raw_workspace.get("path", "")).strip()
    if not workspace_id:
        raise WorkspaceRegistryError("workspace 定義には `id` が必要です。")

    raw_allowed_agents = raw_workspace.get("allowed_agents", [])
    if not isinstance(raw_allowed_agents, list):
        raise WorkspaceRegistryError(
            f"`allowed_agents` は配列で指定してください: {workspace_id}"
        )

    allowed_agents = tuple(str(agent).strip() for agent in raw_allowed_agents if str(agent).strip())
    description = raw_workspace.get("description")
    normalized_description = str(description).strip() if description is not None else None

    return ManagedWorkspace(
        workspace_id=workspace_id,
        path=resolve_workspace_path(
            workspace_value=workspace_path,
            base_dir=registry_base_dir,
            control_root=control_root,
        ),
        allowed_agents=allowed_agents,
        description=normalized_description or None,
    )
